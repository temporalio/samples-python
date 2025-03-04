import asyncio
import uuid
from datetime import datetime, timedelta

from temporalio import activity, workflow
from temporalio.client import Client
from temporalio.common import RetryPolicy
from temporalio.worker import Worker

with workflow.unsafe.imports_passed_through():
    from httpx import HTTPStatusError, Request, Response

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
class MyWorkflow:
    @workflow.run
    async def run(self) -> str:
        return await workflow.execute_activity(
            my_activity,
            start_to_close_timeout=timedelta(seconds=10),
            retry_policy=RetryPolicy(initial_interval=timedelta(seconds=2)),
        )


async def main():
    client = await Client.connect("localhost:7233")
    async with Worker(
        client,
        task_queue="activity-retries-task-queue",
        workflows=[MyWorkflow],
        activities=[my_activity],
    ):
        result = await client.execute_workflow(
            MyWorkflow.run,
            id=str(uuid.uuid4()),
            task_queue="activity-retries-task-queue",
        )
        print(f"Result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
