import asyncio
import logging

from temporalio.client import Client
from temporalio.common import WorkflowIDReusePolicy
from temporalio.envconfig import ClientConfig

from workflow_pause.updates import TASK_QUEUE, WORKFLOW_ID
from workflow_pause.updates.workflow import UpdatePauseWorkflow


async def main():
    logging.basicConfig(level=logging.INFO)

    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")
    client = await Client.connect(**config)

    handle = await client.start_workflow(
        UpdatePauseWorkflow.run,
        id=WORKFLOW_ID,
        task_queue=TASK_QUEUE,
        id_reuse_policy=WorkflowIDReusePolicy.TERMINATE_IF_RUNNING,
    )
    print(f"Started workflow with ID: {handle.id}")
    print(
        f"Update it with:   temporal workflow update execute -w {WORKFLOW_ID} "
        f"--name add --input 5"
    )
    print(f"Pause it with:    temporal workflow pause -w {WORKFLOW_ID} --reason demo")


if __name__ == "__main__":
    asyncio.run(main())
