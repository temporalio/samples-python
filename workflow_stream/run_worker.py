from __future__ import annotations

import asyncio
import logging

from temporalio.client import Client
from temporalio.worker import Worker

from workflow_stream.activities.payment_activity import charge_card
from workflow_stream.shared import TASK_QUEUE
from workflow_stream.workflows.order_workflow import OrderWorkflow


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    client = await Client.connect("localhost:7233")
    worker = Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[OrderWorkflow],
        activities=[charge_card],
    )
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
