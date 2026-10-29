import asyncio
from dataclasses import dataclass

from claude_agent_sdk import (
    ClaudeAgentOptions,
    ClaudeSDKClient,
    CLIConnectionError,
    ResultMessage,
    SystemMessage,
)
from temporalio import workflow
from temporalio.claude_agent_sdk import TemporalTransport


@dataclass
class Branch:
    session_id: str
    prompt: str
    answer: str


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
        self, *, resume: str | None = None, fork_session: bool = False
    ) -> ClaudeAgentOptions:
        """Options that start a new session, or continue the one given by resume.

        With fork_session, resume is the session to fork from, and the fork is a
        new session.
        """
        return ClaudeAgentOptions(
            setting_sources=[],
            env={"CLAUDE_CODE_RESUME_INTERRUPTED_TURN": "1"},
            resume=resume,
            fork_session=fork_session,
        )

    async def ask(self, prompt: str, fork_from: str | None = None) -> Branch:
        """Answer the prompt, in a fork of fork_from if given.

        Resumes the session if the connection is lost.
        """
        session_id = None  # Claude Code's, once it has the prompt

        while True:
            try:
                if session_id is not None:
                    options = self.options(resume=session_id)
                elif fork_from is not None:
                    options = self.options(resume=fork_from, fork_session=True)
                else:
                    options = self.options()

                transport = TemporalTransport(options)
                async with ClaudeSDKClient(
                    options=options, transport=transport
                ) as client:
                    # Keep sending the prompt until Claude Code reports a session, which
                    # means it received it. After that, a resume finishes the turn.
                    if session_id is None:
                        await client.query(prompt)

                    async for message in client.receive_response():
                        if (
                            isinstance(message, SystemMessage)
                            and message.subtype == "init"
                        ):
                            session_id = message.data["session_id"]
                        elif isinstance(message, ResultMessage):
                            return Branch(
                                message.session_id, prompt, message.result or ""
                            )

                raise RuntimeError("Claude Code ended the turn without a result")

            except CLIConnectionError:
                # Resume the fork if Claude Code started it, or start it again.
                pass
