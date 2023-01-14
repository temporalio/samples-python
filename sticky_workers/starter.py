import asyncio
from tabnanny import check
from uuid import uuid4

from temporalio.client import Client

from sticky_workers.tasks import FileProcessing


async def main():
    # Connect client
    client = await Client.connect("localhost:7233")

    # Start 10 concurrent workflows
    futures = []
    for _ in range(10):
        handle = client.execute_workflow(
            FileProcessing.run, id=str(uuid4()), task_queue="distribution-queue"
        )
        await asyncio.sleep(0.1)
        futures.append(handle)

    checksums = await asyncio.gather(*futures)
    print("\n".join([f"Output checksums:"] + checksums))


if __name__ == "__main__":
    asyncio.run(main())
