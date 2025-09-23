import asyncio
import logging
from temporalio.client import Client
from temporalio.worker import Worker

from multiline_logging.activities import failing_activity, complex_failing_activity
from multiline_logging.interceptor import MultilineLoggingInterceptor
from multiline_logging.workflows import MultilineLoggingWorkflow

logging.basicConfig(level=logging.INFO)

async def main():
    client = await Client.connect("localhost:7233")

    worker = Worker(
        client,
        task_queue="multiline-logging-task-queue",
        workflows=[MultilineLoggingWorkflow],
        activities=[failing_activity, complex_failing_activity],
        interceptors=[MultilineLoggingInterceptor()],
    )

    print("Worker started. Ctrl+C to exit.")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
