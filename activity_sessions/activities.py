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
        load_seconds: float,
        emit: Callable[[StepEvent], None],
    ) -> None:
        self.worker_identity = worker_identity
        self.load_seconds = load_seconds
        self.emit = emit
        self.cache: dict[str, str] = {}

    @activity.defn
    async def conversation_step(self, step: int) -> None:
        info = activity.info()
        # Only standalone activities lack workflow IDs; this sample calls it from a workflow.
        workflow_id = cast(str, info.workflow_id)
        run_id = cast(str, info.workflow_run_id)
        cache_hit = run_id in self.cache
        self.emit(StepEvent(workflow_id, step, self.worker_identity, cache_hit, False))
        if not cache_hit:
            # Stands in for a slow fetch of conversation history from an external store.
            await asyncio.sleep(self.load_seconds)
            self.cache[run_id] = f"Conversation context for {workflow_id}"
        self.emit(StepEvent(workflow_id, step, self.worker_identity, cache_hit, True))
