import asyncio

from temporalio.client import Client
from temporalio.envconfig import ClientConfig

from reqrespupdate.workflow import UppercaseWorkflow, UppercaseWorkflowInput

WORKFLOW_ID = "reqrespupdate-workflow-id"
TASK_QUEUE = "reqrespupdate-task-queue"


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
