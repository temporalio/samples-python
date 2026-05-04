from __future__ import annotations

import asyncio
from datetime import timedelta

from temporalio import activity
from temporalio.contrib.workflow_streams import WorkflowStreamClient

from workflow_streams.shared import TOPIC_PROGRESS, ProgressEvent


@activity.defn
async def charge_card(order_id: str) -> str:
    """Pretend to charge a card, publishing progress to the parent workflow.

    `WorkflowStreamClient.from_within_activity()` reads the parent
    workflow id and the Temporal client from the activity context, so
    this activity can push events back without any wiring.
    """
    client = WorkflowStreamClient.from_within_activity(
        batch_interval=timedelta(milliseconds=200)
    )
    async with client:
        progress = client.topic(TOPIC_PROGRESS, type=ProgressEvent)
        progress.publish(ProgressEvent(message="charging card..."))
        await asyncio.sleep(1.0)
        progress.publish(
            ProgressEvent(message="card charged"),
        )
    return f"charge-{order_id}"
