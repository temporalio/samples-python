import asyncio

from temporalio.client import Client
from temporalio.worker import UnsandboxedWorkflowRunner, Worker

from hello_nexus.handler.dbclient import MyDBClient
from hello_nexus.handler.nexus_service import MyNexusService
from hello_nexus.handler.workflows import HelloWorkflow

interrupt_event = asyncio.Event()


async def main():
    client = await Client.connect(
        "localhost:7233", namespace="my-target-namespace-python"
    )
    task_queue = "my-target-task-queue-python"

    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[HelloWorkflow],
        nexus_services=[MyNexusService(db_client=MyDBClient())],
        workflow_runner=UnsandboxedWorkflowRunner(),
    ):
        print("Handler worker started")
        await asyncio.Future()


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        interrupt_event.set()
        loop.run_until_complete(loop.shutdown_asyncgens())
