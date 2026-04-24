from datetime import timedelta
from typing import Dict, Optional

from temporalio import common, workflow

from models import (
    AGGREGATOR_WORKFLOW_ID,
    TASK_QUEUE,
    SurveyResponse,
    SurveyResponseInput,
    TallyResult,
)

with workflow.unsafe.imports_passed_through():
    from activities import record_response

__all__ = [
    "TASK_QUEUE",
    "SurveyResponseInput",
    "SurveyResponseWorkflow",
    "PollAggregatorWorkflow",
]


@workflow.defn(versioning_behavior=common.VersioningBehavior.AUTO_UPGRADE)
class SurveyResponseWorkflow:
    @workflow.run
    async def run(self, input: SurveyResponseInput) -> str:
        workflow.logger.info(
            "SurveyResponseWorkflow: user=%s response=%s",
            input.user_id,
            input.response,
        )
        result = await workflow.execute_activity(
            record_response,
            input,
            start_to_close_timeout=timedelta(seconds=180),
            heartbeat_timeout=timedelta(seconds=10),
        )

        # Best-effort signal to the aggregator. S3 is the source of truth;
        # if the aggregator isn't running, we log and continue so the vote
        # is still recorded.
        try:
            handle = workflow.get_external_workflow_handle_for(
                PollAggregatorWorkflow.run, AGGREGATOR_WORKFLOW_ID
            )
            await handle.signal(PollAggregatorWorkflow.submit_vote, input.response)
        except Exception as e:
            workflow.logger.warning("Aggregator signal failed (non-fatal): %s", e)

        workflow.logger.info("SurveyResponseWorkflow completed: %s", result)
        return result


# History-length threshold before continue-as-new. ~2,500 signals per cycle.
_CAN_HISTORY_LENGTH = 5_000


@workflow.defn(versioning_behavior=common.VersioningBehavior.AUTO_UPGRADE)
class PollAggregatorWorkflow:
    def __init__(self) -> None:
        self._counts: Dict[str, int] = {r.value: 0 for r in SurveyResponse}
        self._total: int = 0
        self._last_updated: Optional[str] = None

    @workflow.run
    async def run(self, seed: Optional[TallyResult] = None) -> None:
        if seed is not None:
            # Merge seed into defaults so new enum values added post-seed
            # stay in the counts map.
            for key, value in seed.counts.items():
                self._counts[key] = value
            self._total = seed.total
            self._last_updated = seed.last_updated

        # Stay alive indefinitely; signals mutate state. When history grows
        # too large, continue-as-new and seed the next run with the tally.
        await workflow.wait_condition(
            lambda: workflow.info().get_current_history_length() > _CAN_HISTORY_LENGTH
        )
        workflow.continue_as_new(self._snapshot())

    @workflow.signal
    async def reset(self) -> None:
        """Zero the live tally. S3 audit log is untouched."""
        self._counts = {r.value: 0 for r in SurveyResponse}
        self._total = 0
        self._last_updated = workflow.now().isoformat()

    @workflow.signal
    async def submit_vote(self, response: SurveyResponse) -> None:
        # Defensive coercion: signals may arrive with a raw str or a char list
        # (same converter quirk as SurveyResponseInput.__post_init__).
        key: str
        if isinstance(response, SurveyResponse):
            key = response.value
        elif isinstance(response, list):
            key = "".join(response)
        else:
            key = str(response)
        if key not in self._counts:
            self._counts[key] = 0
        self._counts[key] += 1
        self._total += 1
        self._last_updated = workflow.now().isoformat()

    @workflow.query
    def tally(self) -> TallyResult:
        return self._snapshot()

    def _snapshot(self) -> TallyResult:
        return TallyResult(
            counts=dict(self._counts),
            total=self._total,
            last_updated=self._last_updated,
        )
