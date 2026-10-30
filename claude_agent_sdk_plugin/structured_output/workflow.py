from typing import Literal

from claude_agent_sdk import (
    ClaudeAgentOptions,
    ClaudeSDKClient,
    CLIConnectionError,
    ResultMessage,
    SystemMessage,
    UserMessage,
)
from pydantic import BaseModel, Field
from temporalio import workflow
from temporalio.claude_agent_sdk import TemporalTransport
from temporalio.exceptions import ApplicationError


class SupportTicket(BaseModel):
    category: Literal["billing", "bug", "feature_request"]
    priority: int = Field(ge=1, le=5)
    summary: str


# The text Claude Code sends itself to continue an interrupted turn.
CONTINUE = "Continue from where you left off."


@workflow.defn
class TriageTicketWorkflow:
    @workflow.run
    async def run(self, text: str) -> SupportTicket:
        prompt = f"Triage this customer message:\n{text}"
        return await self.ask(prompt)

    def options(
        self, session_id: str | None = None, prompt_id: str | None = None
    ) -> ClaudeAgentOptions:
        """Options that start a new session, or redo the turn from prompt_id in session_id."""
        return ClaudeAgentOptions(
            output_format={
                "type": "json_schema",
                "schema": SupportTicket.model_json_schema(),
            },
            setting_sources=[],
            # Required to receive the prompt's UUID in the response stream.
            extra_args={"replay-user-messages": None},
            resume=session_id if prompt_id else None,
            resume_session_at=prompt_id,
        )

    async def ask(self, prompt: str) -> SupportTicket:
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
                            if message.structured_output is not None:
                                return SupportTicket.model_validate(
                                    message.structured_output
                                )

                raise ApplicationError(
                    "Claude Code returned no structured output", non_retryable=True
                )

            except CLIConnectionError:
                # Redo the turn from the prompt if Claude Code saved it, or start again.
                pass
