import asyncio
import logging
import os
from dataclasses import dataclass
from datetime import timedelta

import sentry_sdk
from sentry.activities import compose_greeting
from sentry.workflows import GreetingWorkflow
from temporalio.client import Client
from temporalio.worker import Worker

from sentry.interceptor import SentryInterceptor


async def main():
    # Uncomment the line below to see logging
    # logging.basicConfig(level=logging.INFO)

    # Initialize the Sentry SDK
    sentry_sdk.init(
        dsn=os.environ.get("SENTRY_DSN"),
    )

    # Start client
    client = await Client.connect("localhost:7233")

    # Run a worker for the workflow
    worker = Worker(
        client,
        task_queue="sentry-task-queue",
        workflows=[GreetingWorkflow],
        activities=[compose_greeting],
        interceptors=[SentryInterceptor()],  # Use SentryInterceptor for error reporting
    )

    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
