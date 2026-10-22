import asyncio
from collections.abc import Callable
from typing import cast

from temporalio import activity

from activity_sessions import StepEvent


class ConversationActivities:
    """Activities sharing one worker-local cache; each worker process has its own."""

    def __init__(
        self,
        worker_identity: str,
        fetch_seconds: float,
        emit: Callable[[StepEvent], None],
    ) -> None:
        self.worker_identity = worker_identity
        self.fetch_seconds = fetch_seconds
        self.emit = emit
        # Workflow Run ID -> conversation turns this worker holds, always a prefix.
        self.cache: dict[str, list[str]] = {}

    @activity.defn
    async def conversation_step(self, step: int) -> None:
        """Run turn `step`, which needs every earlier turn of the conversation."""
        info = activity.info()
        # Only standalone activities lack workflow IDs; this sample calls it from a workflow.
        workflow_id = cast(str, info.workflow_id)
        run_id = cast(str, info.workflow_run_id)
        turns = self.cache.setdefault(run_id, [])
        missing = range(len(turns), step)
        self.emit(
            StepEvent(workflow_id, step, self.worker_identity, len(missing), False)
        )
        for turn in missing:
            # Stands in for a slow fetch of one turn from an external conversation store.
            await asyncio.sleep(self.fetch_seconds)
            turns.append(f"Turn {turn} of {workflow_id}")
        turns.append(f"Turn {step} of {workflow_id}")
        self.emit(
            StepEvent(workflow_id, step, self.worker_identity, len(missing), True)
        )
