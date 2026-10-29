from typing import Literal

from claude_agent_sdk import (
    ClaudeAgentOptions,
    ClaudeSDKClient,
    CLIConnectionError,
    ResultMessage,
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
    @workflow.init
    def __init__(self, text: str) -> None:
        # Chosen here, so the Workflow can resume the session even mid-turn.
        self.session_id = str(workflow.uuid4())
        self.client = self.new_client(session_id=self.session_id)

    @workflow.run
    async def run(self, text: str) -> SupportTicket:
        await self.client.connect()
        try:
            await self.client.query(f"Triage this customer message:\n{text}")
            result = await self.reply()
        except CLIConnectionError:
            result = await self.resume()

        await self.client.disconnect()
        return result

    def new_client(
        self, *, session_id: str | None = None, resume: str | None = None
    ) -> ClaudeSDKClient:
        """A client that creates the session with session_id, or continues it with resume."""
        options = ClaudeAgentOptions(
            output_format={
                "type": "json_schema",
                "schema": SupportTicket.model_json_schema(),
            },
            setting_sources=[],
            env={"CLAUDE_CODE_RESUME_INTERRUPTED_TURN": "1"},
            session_id=session_id,
            resume=resume,
        )
        return ClaudeSDKClient(options=options, transport=TemporalTransport(options))

    async def resume(self) -> SupportTicket:
        """Resume the session until Claude Code finishes the cut-off turn."""
        while True:
            await self.client.disconnect()
            self.client = self.new_client(resume=self.session_id)
            try:
                await self.client.connect()
                return await self.reply()
            except CLIConnectionError:
                continue

    async def reply(self) -> SupportTicket:
        async for message in self.client.receive_response():
            if (
                isinstance(message, ResultMessage)
                and message.structured_output is not None
            ):
                return SupportTicket.model_validate(message.structured_output)
        raise ApplicationError(
            "Claude Code returned no structured output", non_retryable=True
        )
