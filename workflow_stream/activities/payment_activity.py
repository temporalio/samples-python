from __future__ import annotations

import asyncio
from datetime import timedelta

from temporalio import activity
from temporalio.contrib.workflow_stream import WorkflowStreamClient

from workflow_stream.shared import TOPIC_PROGRESS, ProgressEvent


@activity.defn
async def charge_card(order_id: str) -> str:
    """Pretend to charge a card, publishing progress to the parent workflow.

    `WorkflowStreamClient.from_activity()` reads the parent workflow id
    and the Temporal client from the activity context, so this activity
    can push events back without any wiring.

    Caveat: each call to ``from_activity()`` creates a fresh client with
    a random ``publisher_id``, so dedup does not protect against an
    activity retry republishing the same events. For activities that
    must be exactly-once on the stream side, derive a stable
    ``publisher_id`` from ``activity.info().activity_id`` (this is
    invariant across attempts of the same scheduled activity). The
    current ``WorkflowStreamClient`` API does not yet expose
    ``publisher_id`` on its constructors; this sample accepts
    at-most-once-per-attempt semantics.
    """
    client = WorkflowStreamClient.from_activity(
        batch_interval=timedelta(milliseconds=200)
    )
    async with client:
        client.publish(TOPIC_PROGRESS, ProgressEvent(message="charging card..."))
        await asyncio.sleep(1.0)
        client.publish(
            TOPIC_PROGRESS,
            ProgressEvent(message="card charged"),
            force_flush=True,
        )
    return f"charge-{order_id}"
