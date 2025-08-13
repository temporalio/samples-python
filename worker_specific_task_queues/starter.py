import asyncio
from uuid import uuid4

from temporalio.client import Client
from temporalio.envconfig import ClientConfigProfile

from worker_specific_task_queues.tasks import FileProcessing


async def main():
    # Connect client
    config_dict = ClientConfigProfile.load().to_dict()
    config_dict.setdefault("address", "localhost:7233")
    config = ClientConfigProfile.from_dict(config_dict)
    client = await Client.connect(**config.to_client_connect_config())

    # Start 10 concurrent workflows
    futures = []
    for idx in range(10):
        result = client.execute_workflow(
            FileProcessing.run,
            id=f"worker_specific_task_queue-workflow-id-{idx}",
            task_queue="worker_specific_task_queue-distribution-queue",
        )
        await asyncio.sleep(0.1)
        futures.append(result)

    checksums = await asyncio.gather(*futures)
    print("\n".join([f"Output checksums:"] + checksums))


if __name__ == "__main__":
    asyncio.run(main())
