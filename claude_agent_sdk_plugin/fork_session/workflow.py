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


@dataclass
class Branch:
    session_id: str
    prompt: str
    answer: str


# The text Claude Code sends itself to continue an interrupted turn.
CONTINUE = "Continue from where you left off."


@workflow.defn
class ForkSessionWorkflow:
    @workflow.run
    async def run(self, prompt: str, follow_ups: list[str]) -> list[Branch]:
        """Answer the prompt, then each follow-up in a fork of that conversation."""
        base = await self.ask(prompt)

        # Each fork starts from the base conversation and leaves it as it was.
        return list(
            await asyncio.gather(
                *(self.ask(follow_up, base.session_id) for follow_up in follow_ups)
            )
        )

    def options(
        self,
        *,
        resume: str | None = None,
        fork_session: bool = False,
        prompt_id: str | None = None,
    ) -> ClaudeAgentOptions:
        """Options that start a new session, or continue the one given by resume.

        With fork_session, resume is the session to fork from, and the fork is a
        new session. With prompt_id, the session continues from that prompt.
        """
        return ClaudeAgentOptions(
            setting_sources=[],
            # Required to receive the prompt's UUID in the response stream.
            extra_args={"replay-user-messages": None},
            resume=resume,
            fork_session=fork_session,
            resume_session_at=prompt_id,
        )

    async def ask(self, prompt: str, fork_from: str | None = None) -> Branch:
        """Answer the prompt, in a fork of fork_from if given.

        Redoes the turn if the connection is lost.
        """
        session_id = None  # Claude Code's, once it started
        prompt_id = None  # The prompt's, once Claude Code saved it

        while True:
            try:
                if prompt_id is not None:
                    options = self.options(resume=session_id, prompt_id=prompt_id)
                elif fork_from is not None:
                    options = self.options(resume=fork_from, fork_session=True)
                else:
                    options = self.options()

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
                            return Branch(
                                message.session_id, prompt, message.result or ""
                            )

                raise RuntimeError("Claude Code ended the turn without a result")

            except CLIConnectionError:
                # Redo the turn from the prompt if Claude Code saved it, or start again.
                pass
