"""Activity interrupt: ``InterruptException`` raised from a Temporal activity.

The plugin's failure converter preserves the ``Interrupt`` payload across the
activity boundary, so a Temporal activity can pause the agent for human input
the same way a hook can.

For this to work, ``StrandsPlugin`` must be attached to the **client** (not
just the worker) so the failure converter is installed on the data converter.
The worker in this sample does exactly that.
"""

from datetime import timedelta
from typing import Optional

from strands.interrupt import Interrupt, InterruptException
from strands.types.interrupt import InterruptResponseContent
from temporalio import activity, workflow
from temporalio.contrib.strands import TemporalAgent
from temporalio.contrib.strands.workflow import activity_as_tool

# Tracks names that have been approved out-of-band. In a real system, this
# would be a row in a policy database; the human reviewer flips a flag during
# the pause, and the activity's next attempt reads the new value and proceeds.
_APPROVED: set[str] = set()


# @@@SNIPSTART python-strands-activity-interrupt-activity
@activity.defn
async def delete_thing(name: str) -> str:
    if name not in _APPROVED:
        _APPROVED.add(name)
        raise InterruptException(
            Interrupt(
                id=f"delete:{name}",
                name="approval",
                reason=f"approve delete of protected resource '{name}'?",
            )
        )
    return f"deleted {name}"
# @@@SNIPEND


@workflow.defn
class ActivityInterruptWorkflow:
    def __init__(self) -> None:
        self.agent = TemporalAgent(
            start_to_close_timeout=timedelta(seconds=60),
            tools=[
                activity_as_tool(
                    delete_thing,
                    start_to_close_timeout=timedelta(seconds=30),
                ),
            ],
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
