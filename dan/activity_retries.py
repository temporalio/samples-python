import asyncio
from datetime import datetime, timedelta

from httpx import HTTPStatusError, Request, Response
from temporalio import activity, workflow
from temporalio.common import RetryPolicy

from dan.utils.client import start_workflow

log_file = open("/tmp/activity_retries.log", "a")


@activity.defn
async def my_activity():
    log_file.write(f"executing activity at {datetime.now()}\n")
    log_file.flush()
    raise HTTPStatusError(
        message="deliberate error in activity",
        request=Request(method="POST", url="https://httpbin.org/post"),
        response=Response(status_code=504, text="deliberate error in activity"),
    )


@workflow.defn
class Workflow:
    @workflow.run
    async def run(self) -> str:
        return await workflow.execute_activity(
            my_activity,
            start_to_close_timeout=timedelta(seconds=10),
            retry_policy=RetryPolicy(initial_interval=timedelta(seconds=2)),
        )


activities = [my_activity]


async def main():
    wf_handle = await start_workflow(Workflow.run)
    print("workflow result:", await wf_handle.result())


if __name__ == "__main__":
    asyncio.run(main())
