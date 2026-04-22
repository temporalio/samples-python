import asyncio

from temporalio.client import Client
from temporalio.envconfig import ClientConfig

from workflows import TASK_QUEUE, SampleWorkflow


async def main() -> None:
    config = ClientConfig.load_client_connect_config()
    client = await Client.connect(**config)
    print("Connected to Temporal Service")

    result = await client.execute_workflow(
        SampleWorkflow.run,
        "Normal Pi Worker!",
        id="mixed-worker-workflow-id-005",
        task_queue=TASK_QUEUE,
    )
    print(f"Workflow result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
