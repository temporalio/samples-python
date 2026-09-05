import asyncio

from temporalio.client import Client
from temporalio.envconfig import ClientConfig

from reqrespupdate import TASK_QUEUE, WORKFLOW_ID
from reqrespupdate.workflow import UppercaseWorkflow, UppercaseWorkflowInput


async def main():
    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")
    client = await Client.connect(**config)

    handle = await client.start_workflow(
        UppercaseWorkflow.run,
        UppercaseWorkflowInput(),
        id=WORKFLOW_ID,
        task_queue=TASK_QUEUE,
    )
    print(f"Started workflow with ID {handle.id}, now run the requester")


if __name__ == "__main__":
    asyncio.run(main())
