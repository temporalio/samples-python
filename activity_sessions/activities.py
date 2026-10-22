from pathlib import Path
from typing import cast

from temporalio import activity

from activity_sessions import StepResult


class ConversationActivities:
    def __init__(
        self, worker_identity: str, session_enabled: bool, context_file: Path
    ) -> None:
        self.worker_identity = worker_identity
        self.session_enabled = session_enabled
        self.context_file = context_file
        self.cache: dict[str, str] = {}

    @activity.defn
    async def conversation_step(self, step: int) -> StepResult:
        run_id = cast(str, activity.info().workflow_run_id)
        cache_hit = run_id in self.cache
        if not cache_hit:
            self.cache[run_id] = self.context_file.read_text()
        context = self.cache[run_id]
        print(
            f"[{self.worker_identity}] step={step} "
            f"cache={'HIT' if cache_hit else 'MISS'} context_size={len(context)}",
            flush=True,
        )
        return StepResult(step, self.worker_identity, self.session_enabled, cache_hit)
