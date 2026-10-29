from claude_agent_sdk import (
    ClaudeAgentOptions,
    ClaudeSDKClient,
    CLIConnectionError,
    ResultMessage,
    SystemMessage,
)
from temporalio import workflow
from temporalio.claude_agent_sdk import TemporalTransport


@workflow.defn
class OpenTelemetryWorkflow:
    @workflow.run
    async def run(self, prompt: str) -> str:
        return await self.ask(prompt)

    def options(self, *, resume: str | None = None) -> ClaudeAgentOptions:
        """Options that start a new session, or continue the one given by resume."""
        return ClaudeAgentOptions(
            setting_sources=[],
            allowed_tools=["Bash"],
            env={"CLAUDE_CODE_RESUME_INTERRUPTED_TURN": "1"},
            resume=resume,
        )

    async def ask(self, prompt: str) -> str:
        """Answer the prompt, resuming the session if the connection is lost."""
        session_id = None  # Claude Code's, once it has the prompt

        while True:
            try:
                options = self.options(resume=session_id)
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
                            return message.result or ""

                raise RuntimeError("Claude Code ended the turn without a result")

            except CLIConnectionError:
                # Resume the session if Claude Code started it, or start again.
                pass
