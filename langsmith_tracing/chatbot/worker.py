"""Worker for the chatbot LangSmith sample."""

import asyncio
import logging
import sys

from temporalio.client import Client
from temporalio.contrib.langsmith import LangSmithPlugin
from temporalio.contrib.pydantic import pydantic_data_converter
from temporalio.envconfig import ClientConfig
from temporalio.worker import Worker

from langsmith_tracing.chatbot.activities import call_openai
from langsmith_tracing.chatbot.workflows import ChatbotWorkflow


async def main():
    logging.basicConfig(level=logging.INFO)

    add_temporal_runs = "--add-temporal-runs" in sys.argv

    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")

    client = await Client.connect(
        **config,
        data_converter=pydantic_data_converter,
        plugins=[
            LangSmithPlugin(
                project_name="langsmith-chatbot",
                add_temporal_runs=add_temporal_runs,
            )
        ],
    )

    worker = Worker(
        client,
        task_queue="langsmith-chatbot-task-queue",
        workflows=[ChatbotWorkflow],
        activities=[call_openai],
    )

    label = "with" if add_temporal_runs else "without"
    print(f"Worker started ({label} Temporal runs in traces), ctrl+c to exit")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
