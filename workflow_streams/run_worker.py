from __future__ import annotations

import asyncio
import logging

from temporalio.client import Client
from temporalio.worker import Worker

from workflow_streams.activities.payment_activity import charge_card
from workflow_streams.shared import TASK_QUEUE
from workflow_streams.workflows.hub_workflow import HubWorkflow
from workflow_streams.workflows.order_workflow import OrderWorkflow
from workflow_streams.workflows.pipeline_workflow import PipelineWorkflow
from workflow_streams.workflows.ticker_workflow import TickerWorkflow


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    client = await Client.connect("localhost:7233")
    worker = Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[HubWorkflow, OrderWorkflow, PipelineWorkflow, TickerWorkflow],
        activities=[charge_card],
    )
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
