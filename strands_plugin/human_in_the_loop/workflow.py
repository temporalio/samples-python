"""Hook-based human-in-the-loop: pause on ``BeforeToolCallEvent.interrupt()``.

A hook gates the ``delete_file`` tool behind human approval. The agent stops
with ``stop_reason == "interrupt"``; the workflow waits for a signal carrying
the approval response, then resumes the agent with the response.
"""

from datetime import timedelta
from typing import Optional

from strands import tool
from strands.hooks import HookProvider, HookRegistry
from strands.hooks.events import BeforeToolCallEvent
from strands.types.interrupt import InterruptResponseContent
from temporalio import workflow
from temporalio.contrib.strands import TemporalAgent


@tool
def delete_file(path: str) -> str:
    return f"deleted {path}"


# @@@SNIPSTART python-strands-human-in-the-loop-hook
class ApprovalHook(HookProvider):
    def register_hooks(self, registry: HookRegistry, **kwargs: object) -> None:
        registry.add_callback(BeforeToolCallEvent, self._gate)

    def _gate(self, event: BeforeToolCallEvent) -> None:
        if event.tool_use["name"] != "delete_file":
            return
        approval = event.interrupt(
            "approval",
            reason=f"approve delete of {event.tool_use['input']['path']}?",
        )
        if approval != "approve":
            event.cancel_tool = "denied"
# @@@SNIPEND


# @@@SNIPSTART python-strands-human-in-the-loop-workflow
@workflow.defn
class HumanInTheLoopWorkflow:
    def __init__(self) -> None:
        self.agent = TemporalAgent(
            start_to_close_timeout=timedelta(seconds=60),
            tools=[delete_file],
            hooks=[ApprovalHook()],
        )
        self._approval: Optional[str] = None
        self._pending_reason: Optional[str] = None

    @workflow.signal
    def approve(self, response: str) -> None:
        self._approval = response

    @workflow.query
    def pending_approval(self) -> Optional[str]:
        return self._pending_reason

    @workflow.run
    async def run(self, prompt: str) -> str:
        result = await self.agent.invoke_async(prompt)
        while result.stop_reason == "interrupt":
            interrupts = list(result.interrupts or [])
            self._pending_reason = interrupts[0].reason if interrupts else None
            await workflow.wait_condition(lambda: self._approval is not None)
            response = self._approval
            self._approval = None
            self._pending_reason = None
            responses: list[InterruptResponseContent] = [
                {"interruptResponse": {"interruptId": i.id, "response": response}}
                for i in interrupts
            ]
            result = await self.agent.invoke_async(responses)
        return str(result)
# @@@SNIPEND
