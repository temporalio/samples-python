from typing import Literal

from claude_agent_sdk import (
    ClaudeAgentOptions,
    ClaudeSDKClient,
    CLIConnectionError,
    ResultMessage,
    SystemMessage,
)
from pydantic import BaseModel, Field
from temporalio import workflow
from temporalio.claude_agent_sdk import TemporalTransport
from temporalio.exceptions import ApplicationError


class SupportTicket(BaseModel):
    category: Literal["billing", "bug", "feature_request"]
    priority: int = Field(ge=1, le=5)
    summary: str


@workflow.defn
class TriageTicketWorkflow:
    @workflow.run
    async def run(self, text: str) -> SupportTicket:
        prompt = f"Triage this customer message:\n{text}"
        return await self.ask(prompt)

    def options(self, *, resume: str | None = None) -> ClaudeAgentOptions:
        """Options that start a new session, or continue the one given by resume."""
        return ClaudeAgentOptions(
            output_format={
                "type": "json_schema",
                "schema": SupportTicket.model_json_schema(),
            },
            setting_sources=[],
            env={"CLAUDE_CODE_RESUME_INTERRUPTED_TURN": "1"},
            resume=resume,
        )

    async def ask(self, prompt: str) -> SupportTicket:
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
                            if message.structured_output is not None:
                                return SupportTicket.model_validate(
                                    message.structured_output
                                )

                raise ApplicationError(
                    "Claude Code returned no structured output", non_retryable=True
                )

            except CLIConnectionError:
                # Resume the session if Claude Code started it, or start again.
                pass
