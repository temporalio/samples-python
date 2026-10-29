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
    SystemMessage,
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
    def __init__(self) -> None:
        self.pending: dict[str, ToolRequest] = {}
        self.decisions: dict[str, bool] = {}

    @workflow.run
    async def run(self, task: str) -> str:
        return await self.ask(task)

    def options(self, *, resume: str | None = None) -> ClaudeAgentOptions:
        """Options that start a new session, or continue the one given by resume."""
        return ClaudeAgentOptions(
            # With permission_mode="default", every Bash command asks can_use_tool.
            tools=["Bash"],
            permission_mode="default",
            can_use_tool=self.ask_human,
            setting_sources=[],
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
