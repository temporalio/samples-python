import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional

from temporalio import exceptions
from temporalio.client import Client
from temporalio.envconfig import ClientConfigProfile

from updatable_timer import TASK_QUEUE
from updatable_timer.workflow import Workflow


async def main(client: Optional[Client] = None):
    logging.basicConfig(level=logging.INFO)

    if not client:
        config = ClientConfig.load_client_connect_config()
        config.setdefault("target_host", "localhost:7233")
        client = await Client.connect(**config)
    try:
        handle = await client.start_workflow(
            Workflow.run,
            (datetime.now() + timedelta(days=1)).timestamp(),
            id=f"updatable-timer-workflow",
            task_queue=TASK_QUEUE,
        )
        logging.info(f"Workflow started: run_id={handle.result_run_id}")
    except exceptions.WorkflowAlreadyStartedError as e:
        logging.info(
            f"Workflow already running: workflow_id={e.workflow_id}, run_id={e.run_id}"
        )


if __name__ == "__main__":
    asyncio.run(main())
