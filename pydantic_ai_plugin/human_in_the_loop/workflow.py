from dataclasses import dataclass
from typing import Literal

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from pydantic_ai import (
        Agent,
        DeferredToolRequests,
        ToolApproved,
        ToolDenied,
    )
    from pydantic_ai.durable_exec.temporal import (
        PydanticAIWorkflow,
        TemporalDurability,
    )
    from pydantic_ai.models.test import TestModel


Decision = Literal["approve", "reject", "cancel"]


@dataclass
class ApprovalInput:
    prompt: str
    model: str | None = None


agent = Agent(
    TestModel(
        call_tools=["delete_record"],
        custom_output_text="The operator decision was applied.",
    ),
    name="approval_agent",
    output_type=[str, DeferredToolRequests],
    capabilities=[TemporalDurability()],
)


@agent.tool_plain(requires_approval=True)
async def delete_record(record_id: str) -> str:
    return f"deleted {record_id}"


@workflow.defn
class ApprovalWorkflow(PydanticAIWorkflow):
    __pydantic_ai_agents__ = [agent]

    def __init__(self) -> None:
        self._decision: Decision | None = None
        self._pending: str | None = None

    @workflow.signal
    def decide(self, decision: Decision) -> None:
        self._decision = decision

    @workflow.query
    def pending_approval(self) -> str | None:
        return self._pending

    @workflow.run
    async def run(self, input: ApprovalInput) -> str:
        first = await agent.run(input.prompt, model=input.model)
        if not isinstance(first.output, DeferredToolRequests):
            return first.output

        calls = first.output.approvals
        self._pending = calls[0].tool_name if calls else None
        await workflow.wait_condition(lambda: self._decision is not None)
        decision = self._decision
        self._pending = None

        if decision == "cancel":
            return "Cancelled by the operator."

        approvals: dict[str, bool | ToolApproved | ToolDenied] = {
            call.tool_call_id: (
                True
                if decision == "approve"
                else ToolDenied(message="Rejected by the operator.")
            )
            for call in calls
        }
        deferred_results = first.output.build_results(approvals=approvals)
        resumed = await agent.run(
            "Continue after the operator decision.",
            message_history=first.all_messages(),
            deferred_tool_results=deferred_results,
            model=input.model,
        )
        assert isinstance(resumed.output, str)
        return resumed.output
