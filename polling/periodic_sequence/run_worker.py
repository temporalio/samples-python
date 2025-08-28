import asyncio

from temporalio.client import Client
from temporalio.envconfig import ClientConfig
from temporalio.worker import Worker

from polling.periodic_sequence.activities import compose_greeting
from polling.periodic_sequence.workflows import ChildWorkflow, GreetingWorkflow


async def main():
    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")
    client = await Client.connect(**config)

    worker = Worker(
        client,
        task_queue="periodic-retry-task-queue",
        workflows=[GreetingWorkflow, ChildWorkflow],
        activities=[compose_greeting],
    )
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
