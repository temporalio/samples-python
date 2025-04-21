import asyncio
from datetime import timedelta

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from custom_metric.activity import print_and_sleep


@workflow.defn
class StartTwoActivitiesWorkflow:
    @workflow.run
    async def run(self):
        # Request two concurrent activities with only one task slot so
        # we can see nontrivial schedule to start times.
        activity1 = workflow.execute_activity(
            print_and_sleep,
            start_to_close_timeout=timedelta(seconds=5),
        )
        activity2 = workflow.execute_activity(
            print_and_sleep,
            start_to_close_timeout=timedelta(seconds=5),
        )
        await asyncio.gather(activity1, activity2)
        return None
