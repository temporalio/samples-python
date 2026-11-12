import json
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
    UserMessage,
)
from temporalio import workflow
from temporalio.claude_agent_sdk import TemporalTransport


@dataclass
class ToolRequest:
    tool_use_id: str
    tool_name: str
    tool_input: dict[str, Any]


# The text Claude Code sends itself to continue an interrupted turn.
CONTINUE = "Continue from where you left off."


@workflow.defn
class HumanInTheLoopWorkflow:
    def __init__(self) -> None:
        self.pending: ToolRequest | None = None
        self.decisions: dict[str, bool] = {}

    @workflow.run
    async def run(self, task: str) -> str:
        return await self.ask(task)

    def options(
        self, session_id: str | None = None, prompt_id: str | None = None
    ) -> ClaudeAgentOptions:
        """Options that start a new session, or redo the turn from prompt_id in session_id."""
        return ClaudeAgentOptions(
            # With permission_mode="default", every Bash command asks can_use_tool.
            tools=["Bash"],
            permission_mode="default",
            # @@@SNIPSTART python-claude-agent-sdk-human-in-the-loop-options
            can_use_tool=self.ask_human,
            # @@@SNIPEND
            setting_sources=[],
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

    # @@@SNIPSTART python-claude-agent-sdk-human-in-the-loop-approval
    async def ask_human(
        self, tool_name: str, tool_input: dict[str, Any], context: ToolPermissionContext
    ) -> PermissionResult:
        # A turn redone after a Worker restart asks again, so reuse the decision.
        call = json.dumps([tool_name, tool_input], sort_keys=True)
        if call not in self.decisions:
            self.pending = ToolRequest(context.tool_use_id or "", tool_name, tool_input)
            try:
                await workflow.wait_condition(lambda: call in self.decisions)
            finally:
                self.pending = None
        if self.decisions[call]:
            return PermissionResultAllow()
        return PermissionResultDeny(message="A person denied this tool call")

    # @@@SNIPEND

    @workflow.query
    def pending_tool_calls(self) -> ToolRequest | None:
        return self.pending

    # @@@SNIPSTART python-claude-agent-sdk-human-in-the-loop-decision
    @workflow.update
    def decide(self, approved: bool) -> None:
        if self.pending is None:
            raise ValueError("No tool call is waiting for a decision")
        # Record the decision before the update completes, even if the callback
        # is interrupted by a lost connection before its wait resumes.
        call = json.dumps(
            [self.pending.tool_name, self.pending.tool_input], sort_keys=True
        )
        self.decisions[call] = approved
        self.pending = None

    # @@@SNIPEND

    @decide.validator
    def validate_decide(self, approved: bool) -> None:
        if self.pending is None:
            raise ValueError("No tool call is waiting for a decision")
