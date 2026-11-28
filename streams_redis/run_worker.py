from __future__ import annotations

import asyncio
import logging

from temporalio.worker import Worker

from streams_redis.activities.model_activity import stream_answer
from streams_redis.shared import TASK_QUEUE, connect
from streams_redis.workflows.agent_workflow import AgentWorkflow


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    worker = Worker(
        await connect(),
        task_queue=TASK_QUEUE,
        workflows=[AgentWorkflow],
        activities=[stream_answer],
    )
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
