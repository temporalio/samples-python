import asyncio
from dataclasses import dataclass

from claude_agent_sdk import (
    ClaudeAgentOptions,
    ClaudeSDKClient,
    CLIConnectionError,
    ResultMessage,
    SystemMessage,
    UserMessage,
)
from temporalio import workflow
from temporalio.claude_agent_sdk import TemporalTransport
from temporalio.exceptions import ApplicationError

# The text Claude Code sends itself to continue an interrupted turn.
CONTINUE = "Continue from where you left off."


@dataclass
class ChatInput:
    session_id: str | None = None
    turns_per_run: int = 3


@workflow.defn
class ChatWorkflow:
    @workflow.init
    def __init__(self, input: ChatInput) -> None:
        self.session_id = input.session_id
        self.turns_per_run = input.turns_per_run
        self.turns = 0
        self.ended = False
        self.client = self.new_client()
        self.connected = False
        self.lock = asyncio.Lock()

    @workflow.run
    async def run(self, input: ChatInput) -> None:
        await workflow.wait_condition(self.run_is_done)

        await self.client.disconnect()

        if self.ended:
            return

        workflow.continue_as_new(ChatInput(self.session_id, self.turns_per_run))

    def new_client(self, prompt_id: str | None = None) -> ClaudeSDKClient:
        """A client that starts Claude Code with a new session, or resumes the session, from prompt_id if given."""
        options = ClaudeAgentOptions(
            setting_sources=[],
            # Required to receive each message's UUID in the response stream.
            extra_args={"replay-user-messages": None},
            resume=self.session_id,  # None starts a new session.
            resume_session_at=prompt_id,
        )

        # The default SubprocessConnector keeps session files on the Worker host,
        # so only that host can resume. With Workers on several hosts, pass
        # activity_options={"connect": {"task_queue": ...}} with a task queue
        # only that host polls.
        return ClaudeSDKClient(options=options, transport=TemporalTransport(options))

    @workflow.update
    async def send_message(self, message: str) -> str:
        """Answer the message in the session, redoing the turn if the connection is lost."""
        self.turns += 1

        # One turn at a time, so each message gets its own reply.
        async with self.lock:
            prompt_id = None  # The message's, once Claude Code saved it

            while True:
                try:
                    # Claude Code starts on the first message, and again after a redo.
                    if not self.connected:
                        await self.client.connect()
                        self.connected = True

                    await self.client.query(CONTINUE if prompt_id else message)

                    async for response in self.client.receive_response():
                        if (
                            isinstance(response, SystemMessage)
                            and response.subtype == "init"
                        ):
                            self.session_id = response.data["session_id"]
                        elif (
                            isinstance(response, UserMessage)
                            and response.uuid
                            and not prompt_id
                        ):
                            prompt_id = response.uuid
                        elif isinstance(response, ResultMessage):
                            return response.result or "\n".join(response.errors or [])

                    raise RuntimeError("Claude Code ended the turn without a result")

                except CLIConnectionError:
                    await self.client.disconnect()
                    self.connected = False
                    # Redo the turn from the message if Claude Code saved it, or send it again.
                    self.client = self.new_client(prompt_id)

    @send_message.validator
    def validate_send_message(self, message: str) -> None:
        if self.ended:
            raise ApplicationError("The conversation has ended")

        if self.run_is_full():
            raise ApplicationError("The chat is continuing as new. Send it again.")

    @workflow.signal
    def end_conversation(self) -> None:
        self.ended = True

    def run_is_done(self) -> bool:
        """The chat ended or this run is full, and every message has its reply."""
        return (self.ended or self.run_is_full()) and workflow.all_handlers_finished()

    def run_is_full(self) -> bool:
        return (
            self.turns >= self.turns_per_run
            or workflow.info().is_continue_as_new_suggested()
        )
