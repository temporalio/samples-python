import asyncio
import logging

from temporalio.client import Client
from temporalio.common import WorkflowIDReusePolicy
from temporalio.envconfig import ClientConfig

from workflow_pause.activities import ACTIVITY_ID, TASK_QUEUE, WORKFLOW_ID
from workflow_pause.activities.workflow import ActivityPauseWorkflow


async def main():
    logging.basicConfig(level=logging.INFO)

    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")
    client = await Client.connect(**config)

    handle = await client.start_workflow(
        ActivityPauseWorkflow.run,
        "widget",
        id=WORKFLOW_ID,
        task_queue=TASK_QUEUE,
        id_reuse_policy=WorkflowIDReusePolicy.TERMINATE_IF_RUNNING,
    )
    print(f"Started workflow with ID: {handle.id}")
    print(
        f"Pause the workflow:  temporal workflow pause -w {WORKFLOW_ID} --reason demo"
    )
    print(
        f"Pause the activity:  temporal activity pause "
        f"--activity-id {ACTIVITY_ID} -w {WORKFLOW_ID}"
    )


if __name__ == "__main__":
    asyncio.run(main())
