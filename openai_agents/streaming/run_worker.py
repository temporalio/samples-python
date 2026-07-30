from __future__ import annotations

import asyncio
import logging
from datetime import timedelta

from temporalio.client import Client
from temporalio.contrib.openai_agents import (
    ModelActivityParameters,
    OpenAIAgentsPlugin,
)
from temporalio.worker import Worker

from openai_agents.streaming.activities.joke_activities import how_many_jokes
from openai_agents.streaming.shared import TASK_QUEUE, TOPIC_EVENTS
from openai_agents.streaming.workflows.stream_items_workflow import (
    StreamItemsWorkflow,
)
from openai_agents.streaming.workflows.stream_text_workflow import (
    StreamTextWorkflow,
)


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    client = await Client.connect(
        "localhost:7233",
        plugins=[
            OpenAIAgentsPlugin(
                model_params=ModelActivityParameters(
                    # The streaming activity heartbeats on a background task,
                    # so a heartbeat_timeout well under start_to_close_timeout
                    # detects a stuck model call early.
                    heartbeat_timeout=timedelta(seconds=10),
                    start_to_close_timeout=timedelta(minutes=5),
                    # Required for Runner.run_streamed: the topic the streaming
                    # activity publishes raw model events to.
                    streaming_topic=TOPIC_EVENTS,
                ),
            ),
        ],
    )

    worker = Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[StreamTextWorkflow, StreamItemsWorkflow],
        activities=[how_many_jokes],
    )
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
