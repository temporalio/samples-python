from datetime import timedelta

from claude_agent_sdk import (
    ClaudeAgentOptions,
    ClaudeSDKClient,
    CLIConnectionError,
    ResultMessage,
)
from temporalio import workflow
from temporalio.claude_agent_sdk import TemporalTransport
from temporalio.contrib.workflow_streams import WorkflowStream


@workflow.defn
class StreamingWorkflow:
    @workflow.init
    def __init__(self, prompt: str) -> None:
        # Chosen here, so the Workflow can resume the session even mid-turn.
        self.session_id = str(workflow.uuid4())
        self.events = WorkflowStream().topic("events")
        self.client = self.new_client(session_id=self.session_id)

    @workflow.run
    async def run(self, prompt: str) -> str:
        await self.client.connect()
        try:
            await self.client.query(prompt)
            result = await self.reply()
        except CLIConnectionError:
            result = await self.resume()

        await self.client.disconnect()
        # Give a subscriber's last poll time to read the final events before the
        # Workflow, and its in-memory stream, completes.
        await workflow.sleep(timedelta(milliseconds=500))
        return result

    def new_client(
        self, *, session_id: str | None = None, resume: str | None = None
    ) -> ClaudeSDKClient:
        """A client that creates the session with session_id, or continues it with resume."""
        options = ClaudeAgentOptions(
            include_partial_messages=True,
            setting_sources=[],
            env={"CLAUDE_CODE_RESUME_INTERRUPTED_TURN": "1"},
            session_id=session_id,
            resume=resume,
        )
        return ClaudeSDKClient(
            options=options, transport=TemporalTransport(options, stream=self.events)
        )

    async def resume(self) -> str:
        """Resume the session until Claude Code finishes the cut-off turn."""
        while True:
            await self.client.disconnect()
            self.client = self.new_client(resume=self.session_id)
            try:
                await self.client.connect()
                return await self.reply()
            except CLIConnectionError:
                continue

    async def reply(self) -> str:
        async for message in self.client.receive_response():
            if isinstance(message, ResultMessage):
                return message.result or ""
        return ""
