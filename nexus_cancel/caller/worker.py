"""
Worker for the caller namespace that executes workflows calling Nexus operations.
"""

import asyncio

from temporalio.client import Client
from temporalio.envconfig import ClientConfig
from temporalio.worker import Worker

from nexus_cancel.caller.workflows import HelloCallerWorkflow

NAMESPACE = "my-caller-namespace"
TASK_QUEUE = "my-caller-workflow-task-queue"


async def main():
    """Start the caller worker."""
    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")
    config.setdefault("namespace", NAMESPACE)
    client = await Client.connect(**config)

    # Start worker with the caller workflow
    worker = Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[HelloCallerWorkflow],
    )

    print(
        f"Starting caller worker on namespace '{NAMESPACE}', task queue '{TASK_QUEUE}'"
    )
    print("Worker is ready to execute caller workflows...")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
