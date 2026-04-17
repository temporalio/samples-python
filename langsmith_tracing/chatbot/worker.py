"""Worker for the chatbot LangSmith sample."""

import asyncio
import logging

from temporalio.client import Client
from temporalio.contrib.langsmith import LangSmithPlugin
from temporalio.contrib.pydantic import pydantic_data_converter
from temporalio.envconfig import ClientConfig
from temporalio.worker import Worker

from langsmith_tracing.chatbot.activities import call_openai, save_note
from langsmith_tracing.chatbot.workflows import ChatbotWorkflow

interrupt_event = asyncio.Event()


async def main():
    logging.basicConfig(level=logging.INFO)

    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")

    client = await Client.connect(
        **config,
        data_converter=pydantic_data_converter,
    )

    plugin = LangSmithPlugin(project_name="langsmith-chatbot")

    async with Worker(
        client,
        task_queue="langsmith-chatbot-task-queue",
        workflows=[ChatbotWorkflow],
        activities=[call_openai, save_note],
        plugins=[plugin],
        max_cached_workflows=0,
    ):
        print("Worker started, ctrl+c to exit")
        await interrupt_event.wait()
        print("Shutting down")


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        interrupt_event.set()
        loop.run_until_complete(loop.shutdown_asyncgens())
