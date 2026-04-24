"""One-shot starter for the PollAggregatorWorkflow singleton.

Safe to run multiple times: if the aggregator is already running,
WorkflowAlreadyStartedError is caught and reported as a no-op.
"""

import asyncio

from temporalio.client import Client
from temporalio.envconfig import ClientConfig
from temporalio.exceptions import WorkflowAlreadyStartedError

from models import AGGREGATOR_TASK_QUEUE, AGGREGATOR_WORKFLOW_ID
from workflows import PollAggregatorWorkflow


async def main() -> None:
    config = ClientConfig.load_client_connect_config()
    client = await Client.connect(**config)
    print("Connected to Temporal Service")

    try:
        await client.start_workflow(
            PollAggregatorWorkflow.run,
            None,
            id=AGGREGATOR_WORKFLOW_ID,
            task_queue=AGGREGATOR_TASK_QUEUE,
        )
        print(f"Started aggregator workflow: id={AGGREGATOR_WORKFLOW_ID}")
    except WorkflowAlreadyStartedError:
        print(f"Aggregator already running: id={AGGREGATOR_WORKFLOW_ID}")


if __name__ == "__main__":
    asyncio.run(main())
