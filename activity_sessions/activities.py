import asyncio

from temporalio import activity
from temporalio.exceptions import ApplicationError

from activity_sessions.models import (
    ACTIVITY_NAME,
    ConversationContext,
    StepInput,
    StepResult,
)
from activity_sessions.storage import FileArtifactStore


class ConversationActivities:
    def __init__(
        self,
        store: FileArtifactStore,
        worker_identity: str,
        session_enabled: bool,
    ) -> None:
        self.store = store
        self.worker_identity = worker_identity
        self.session_enabled = session_enabled
        self.cache: dict[tuple[str, str], ConversationContext] = {}

    @activity.defn(name=ACTIVITY_NAME)
    async def process_conversation_step(self, request: StepInput) -> StepResult:
        run_id = activity.info().workflow_run_id
        if run_id is None:
            raise ApplicationError(
                "This sample requires a workflow activity", non_retryable=True
            )

        cache_key = (run_id, request.input_ref)
        context = self.cache.get(cache_key)
        cache_hit = context is not None
        artifact_reads = 0
        if context is None:
            context = await asyncio.to_thread(self.store.read, request.input_ref)
            artifact_reads += 1
            self.cache[cache_key] = context

        output = ConversationContext(
            messages=[
                *context.messages,
                f"Processed conversation step {request.step}.",
            ],
            completed_steps=[*context.completed_steps, request.step],
        )
        # Persist before advertising the reference: another worker must be able to recover on a miss.
        output_ref = await asyncio.to_thread(self.store.write, output)
        artifact_writes = 1
        self.cache[(run_id, output_ref)] = output
        print(
            f"[{self.worker_identity}] run={run_id} step={request.step} "
            f"cache={'HIT' if cache_hit else 'MISS'} "
            f"artifact_reads={artifact_reads} artifact_writes={artifact_writes}",
            flush=True,
        )
        return StepResult(
            step=request.step,
            worker_identity=self.worker_identity,
            session_enabled=self.session_enabled,
            cache_hit=cache_hit,
            artifact_reads=artifact_reads,
            artifact_writes=artifact_writes,
            output_ref=output_ref,
        )
