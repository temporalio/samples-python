from dataclasses import dataclass
from typing import Any

from claude_agent_sdk import (
    ClaudeAgentOptions,
    ClaudeSDKClient,
    CLIConnectionError,
    PermissionResult,
    PermissionResultAllow,
    PermissionResultDeny,
    ResultMessage,
    ToolPermissionContext,
)
from temporalio import workflow
from temporalio.claude_agent_sdk import TemporalTransport


@dataclass
class ToolRequest:
    tool_use_id: str
    tool_name: str
    tool_input: dict[str, Any]


@dataclass
class Decision:
    tool_use_id: str
    approved: bool


@workflow.defn
class HumanInTheLoopWorkflow:
    @workflow.init
    def __init__(self, task: str) -> None:
        # Chosen here, so the Workflow can resume the session even mid-turn.
        self.session_id = str(workflow.uuid4())
        self.pending: dict[str, ToolRequest] = {}
        self.decisions: dict[str, bool] = {}
        self.client = self.new_client(session_id=self.session_id)

    @workflow.run
    async def run(self, task: str) -> str:
        await self.client.connect()
        try:
            await self.client.query(task)
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
            # With permission_mode="default", every Bash command asks can_use_tool.
            tools=["Bash"],
            permission_mode="default",
            can_use_tool=self.ask_human,
            setting_sources=[],
            env={"CLAUDE_CODE_RESUME_INTERRUPTED_TURN": "1"},
            session_id=session_id,
            resume=resume,
        )
        return ClaudeSDKClient(options=options, transport=TemporalTransport(options))

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

    async def ask_human(
        self, tool_name: str, tool_input: dict[str, Any], context: ToolPermissionContext
    ) -> PermissionResult:
        tool_use_id = context.tool_use_id or ""
        self.pending[tool_use_id] = ToolRequest(tool_use_id, tool_name, tool_input)
        try:
            await workflow.wait_condition(lambda: tool_use_id in self.decisions)
        finally:
            del self.pending[tool_use_id]
        if self.decisions[tool_use_id]:
            return PermissionResultAllow()
        return PermissionResultDeny(message="A person denied this tool call")

    @workflow.query
    def pending_tool_calls(self) -> list[ToolRequest]:
        return list(self.pending.values())

    @workflow.update
    def decide(self, decision: Decision) -> None:
        self.decisions[decision.tool_use_id] = decision.approved

    @decide.validator
    def validate_decide(self, decision: Decision) -> None:
        if decision.tool_use_id not in self.pending:
            raise ValueError(f"No pending tool call {decision.tool_use_id}")
