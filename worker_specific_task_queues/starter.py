import asyncio
from uuid import uuid4

from temporalio.client import Client

from worker_specific_task_queues.tasks import FileProcessing


async def main():
    # Connect client
        # Get repo root - 1 level deep from root
        repo_root = Path(__file__).resolve().parent.parent
        config_file = repo_root / "temporal.toml"
    config = ClientConfig.load_client_connect_config(config_file=str(config_file))
    config["target_host"] = "localhost:7233"
    client = await Client.connect(**config)

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
