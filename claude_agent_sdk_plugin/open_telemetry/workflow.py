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

# The text Claude Code sends itself to continue an interrupted turn.
CONTINUE = "Continue from where you left off."


@workflow.defn
class OpenTelemetryWorkflow:
    @workflow.run
    async def run(self, prompt: str) -> str:
        return await self.ask(prompt)

    def options(
        self, session_id: str | None = None, prompt_id: str | None = None
    ) -> ClaudeAgentOptions:
        """Options that start a new session, or redo the turn from prompt_id in session_id."""
        return ClaudeAgentOptions(
            setting_sources=[],
            allowed_tools=["Bash"],
            # Required to receive the prompt's UUID in the response stream.
            extra_args={"replay-user-messages": None},
            resume=session_id if prompt_id else None,
            resume_session_at=prompt_id,
        )

    async def ask(self, prompt: str) -> str:
        """Answer the prompt, redoing the turn if the connection is lost."""
        session_id = None  # Claude Code's, once it started
        prompt_id = None  # The prompt's, once Claude Code saved it

        while True:
            try:
                options = self.options(session_id, prompt_id)
                transport = TemporalTransport(options)
                async with ClaudeSDKClient(
                    options=options, transport=transport
                ) as client:
                    await client.query(CONTINUE if prompt_id else prompt)

                    async for message in client.receive_response():
                        if (
                            isinstance(message, SystemMessage)
                            and message.subtype == "init"
                        ):
                            session_id = message.data["session_id"]
                        elif (
                            isinstance(message, UserMessage)
                            and message.uuid
                            and not prompt_id
                        ):
                            prompt_id = message.uuid
                        elif isinstance(message, ResultMessage):
                            return message.result or ""

                raise RuntimeError("Claude Code ended the turn without a result")

            except CLIConnectionError:
                # Redo the turn from the prompt if Claude Code saved it, or start again.
                pass
