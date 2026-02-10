"""
Worker for the handler namespace that processes Nexus operations and workflows.
"""

import asyncio

from temporalio.client import Client
from temporalio.envconfig import ClientConfig
from temporalio.worker import Worker

from nexus_cancel.handler.service_handler import MyNexusServiceHandler
from nexus_cancel.handler.workflows import HelloHandlerWorkflow

NAMESPACE = "my-target-namespace"
TASK_QUEUE = "my-handler-task-queue"


async def main():
    """Start the handler worker."""
    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")
    config.setdefault("namespace", NAMESPACE)
    client = await Client.connect(**config)

    # Create the service handler
    service_handler = MyNexusServiceHandler()

    # Start worker with both workflows and Nexus service
    worker = Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[HelloHandlerWorkflow],
        # The nexus_services parameter registers the Nexus service handler
        nexus_services=[service_handler],
    )

    print(
        f"Starting handler worker on namespace '{NAMESPACE}', task queue '{TASK_QUEUE}'"
    )
    print("Worker is ready to process Nexus operations and workflows...")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
