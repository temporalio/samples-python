import asyncio

from temporalio.client import Client
from temporalio.envconfig import ClientConfigProfile
from temporalio.worker import Worker

from polling.periodic_sequence.activities import compose_greeting
from polling.periodic_sequence.workflows import ChildWorkflow, GreetingWorkflow


async def main():
    config_dict = ClientConfigProfile.load().to_dict()
    config_dict.setdefault("address", "localhost:7233")
    config = ClientConfigProfile.from_dict(config_dict)
    client = await Client.connect(**config.to_client_connect_config())

    worker = Worker(
        client,
        task_queue="periodic-retry-task-queue",
        workflows=[GreetingWorkflow, ChildWorkflow],
        activities=[compose_greeting],
    )
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
