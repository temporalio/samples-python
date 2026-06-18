import asyncio
import logging

from temporalio.client import Client
from temporalio.common import WorkflowIDReusePolicy
from temporalio.envconfig import ClientConfig

from workflow_pause.basic import TASK_QUEUE, WORKFLOW_ID
from workflow_pause.basic.workflow import BasicPauseWorkflow


async def main():
    logging.basicConfig(level=logging.INFO)

    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")
    client = await Client.connect(**config)

    handle = await client.start_workflow(
        BasicPauseWorkflow.run,
        20,
        id=WORKFLOW_ID,
        task_queue=TASK_QUEUE,
        id_reuse_policy=WorkflowIDReusePolicy.TERMINATE_IF_RUNNING,
    )
    print(f"Started workflow with ID: {handle.id}")
    print(f"Pause it with:    temporal workflow pause -w {WORKFLOW_ID} --reason demo")
    print(f"Unpause it with:  temporal workflow unpause -w {WORKFLOW_ID}")


if __name__ == "__main__":
    asyncio.run(main())
