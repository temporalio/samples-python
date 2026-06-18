import asyncio
import logging

from temporalio.client import Client
from temporalio.common import WorkflowIDReusePolicy
from temporalio.envconfig import ClientConfig

from workflow_pause.cancel_terminate import TASK_QUEUE, WORKFLOW_ID
from workflow_pause.cancel_terminate.workflow import CancelTerminatePauseWorkflow


async def main():
    logging.basicConfig(level=logging.INFO)

    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")
    client = await Client.connect(**config)

    handle = await client.start_workflow(
        CancelTerminatePauseWorkflow.run,
        20,
        id=WORKFLOW_ID,
        task_queue=TASK_QUEUE,
        id_reuse_policy=WorkflowIDReusePolicy.TERMINATE_IF_RUNNING,
    )
    print(f"Started workflow with ID: {handle.id}")
    print(f"Pause it with:      temporal workflow pause -w {WORKFLOW_ID} --reason demo")
    print(f"Terminate it with:  temporal workflow terminate -w {WORKFLOW_ID}")
    print(f"Cancel it with:     temporal workflow cancel -w {WORKFLOW_ID}")


if __name__ == "__main__":
    asyncio.run(main())
