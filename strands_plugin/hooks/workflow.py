"""Two-hook audit example.

``AuditHook`` subscribes two callbacks to ``AfterToolCallEvent``:

* An in-workflow callback that mutates per-workflow state. It runs in workflow
  context, so it must be deterministic — pure data manipulation only.
* An ``activity_as_hook`` callback that dispatches to a Temporal activity. Use
  this for anything with I/O: writing to an audit log, calling out to a
  metrics system, alerting, etc.
"""

from datetime import timedelta

from strands import tool
from strands.hooks import HookProvider, HookRegistry
from strands.hooks.events import AfterToolCallEvent
from temporalio import activity, workflow
from temporalio.contrib.strands import TemporalAgent
from temporalio.contrib.strands.workflow import activity_as_hook


@activity.defn
async def persist_tool_call(tool_name: str) -> None:
    # In production, write to a database / S3 / your audit pipeline.
    activity.logger.info(f"audit: tool {tool_name} completed")


@tool
def echo(text: str) -> str:
    return text


class AuditHook(HookProvider):
    def __init__(self) -> None:
        self.fired: list[str] = []

    def register_hooks(self, registry: HookRegistry, **kwargs: object) -> None:
        registry.add_callback(AfterToolCallEvent, self._record)
        registry.add_callback(
            AfterToolCallEvent,
            activity_as_hook(
                persist_tool_call,
                activity_input=lambda event: event.tool_use["name"],
                start_to_close_timeout=timedelta(seconds=15),
            ),
        )

    def _record(self, event: AfterToolCallEvent) -> None:
        self.fired.append(event.tool_use["name"])


@workflow.defn
class HooksWorkflow:
    def __init__(self) -> None:
        self.hook = AuditHook()
        self.agent = TemporalAgent(
            start_to_close_timeout=timedelta(seconds=60),
            tools=[echo],
            hooks=[self.hook],
        )

    @workflow.run
    async def run(self, prompt: str) -> list[str]:
        await self.agent.invoke_async(prompt)
        return self.hook.fired
