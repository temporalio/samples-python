import asyncio

from temporalio.client import Client

# from batch_daily.activity import
from batch_daily.workflows import DailyBatchWorkflowInput, TASK_QUEUE_NAME, DailyBatch


async def main():
    client = await Client.connect(
        "localhost:7233",
    )

    result = await client.execute_workflow(
        DailyBatch.run,
        DailyBatchWorkflowInput(
            start_day="2024-01-01",
            end_day="2024-03-01",
            record_filter="taste=yummy",
        ),
        id=f"daily_batch-workflow-id",
        task_queue=TASK_QUEUE_NAME,
    )
    print(f"Workflow result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
