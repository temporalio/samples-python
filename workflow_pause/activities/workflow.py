from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

from workflow_pause.activities import ACTIVITY_ID

with workflow.unsafe.imports_passed_through():
    from workflow_pause.activities.activities import process_item


@workflow.defn
class ActivityPauseWorkflow:
    """Runs a single long-running, retrying activity.

    Two things to demonstrate:
      1. Pausing the *workflow* while the activity is in flight: the running
         activity attempt is not killed, but once it finishes the next workflow
         task is not dispatched, so the workflow does not advance until unpause.
      2. Pausing the *activity* with `temporal activity pause`: retries stop
         after the current attempt ends, and resume on `temporal activity unpause`.
    """

    @workflow.run
    async def run(self, item: str) -> str:
        return await workflow.execute_activity(
            process_item,
            item,
            activity_id=ACTIVITY_ID,
            start_to_close_timeout=timedelta(seconds=30),
            heartbeat_timeout=timedelta(seconds=10),
            retry_policy=RetryPolicy(
                initial_interval=timedelta(seconds=3),
                backoff_coefficient=2.0,
                maximum_attempts=10,
            ),
        )
