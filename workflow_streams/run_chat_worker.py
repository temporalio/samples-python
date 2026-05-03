"""Worker for the LLM-streaming scenario.

Runs separately from ``run_worker.py`` so the ``openai`` dependency
and the ``OPENAI_API_KEY`` requirement stay isolated to this one
scenario. Different task queue too — the other four samples won't
route work to this worker.

Kill this worker mid-stream while ``run_chat.py`` is running to
trigger a retry: Temporal restarts the activity on the next worker
to come up, the activity publishes a ``RetryEvent`` on its second
attempt, and the consumer resets its rendered output.
"""

from __future__ import annotations

import asyncio
import logging

from temporalio.client import Client
from temporalio.worker import Worker

from workflow_streams.activities.chat_activity import stream_completion
from workflow_streams.chat_shared import CHAT_TASK_QUEUE
from workflow_streams.workflows.chat_workflow import ChatWorkflow


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    client = await Client.connect("localhost:7233")
    worker = Worker(
        client,
        task_queue=CHAT_TASK_QUEUE,
        workflows=[ChatWorkflow],
        activities=[stream_completion],
    )
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
