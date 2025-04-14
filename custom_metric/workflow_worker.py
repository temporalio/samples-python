import asyncio
from datetime import timedelta

from temporalio import workflow
from temporalio.client import Client
from temporalio.worker import Worker

with workflow.unsafe.imports_passed_through():
    from custom_metric.activity_worker import print_message


@workflow.defn
class ExecuteActivityWorkflow:

    @workflow.run
    async def run(self):
        await workflow.execute_activity(
            print_message,
            start_to_close_timeout=timedelta(seconds=5),
        )
        return None


async def main():

    client = await Client.connect(
        "localhost:7233",
    )
    worker = Worker(
        client,
        task_queue="custom-metric-task-queue",
        workflows=[ExecuteActivityWorkflow],
    )

    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
