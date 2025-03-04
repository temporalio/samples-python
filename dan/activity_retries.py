import asyncio
from datetime import datetime, timedelta

from temporalio import activity, workflow
from temporalio.common import RetryPolicy

from dan.utils.client import start_workflow

log_file = open("/tmp/activity_retries.log", "a")


@activity.defn
async def hello_activity() -> str:
    log_file.write(f"executing activity at {datetime.now()}\n")
    log_file.flush()
    raise Exception("deliberate error in activity")
    return "activity-result 1"


@workflow.defn
class Workflow:
    @workflow.run
    async def run(self) -> str:
        return await workflow.execute_activity(
            hello_activity,
            start_to_close_timeout=timedelta(seconds=10),
            retry_policy=RetryPolicy(initial_interval=timedelta(seconds=2)),
        )


activities = [hello_activity]


async def main():
    wf_handle = await start_workflow(Workflow.run)
    print("workflow result:", await wf_handle.result())


if __name__ == "__main__":
    asyncio.run(main())
