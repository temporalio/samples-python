import asyncio
from concurrent.futures import ThreadPoolExecutor

from temporalio.client import Client
from temporalio.worker import Worker

from batch_daily.activities import (
    list_records,
    process_record,
)
from batch_daily.workflows import DailyBatch, RecordBatchProcessor, TASK_QUEUE_NAME


async def main() -> None:
    """Main worker function."""
    client = await Client.connect("localhost:7233")

    worker: Worker = Worker(
        client,
        task_queue=TASK_QUEUE_NAME,
        workflows=[DailyBatch, RecordBatchProcessor],
        activities=[list_records, process_record],
        activity_executor=ThreadPoolExecutor(100),
    )
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
