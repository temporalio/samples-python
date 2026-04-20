"""Worker for the basic LangSmith sample."""

import asyncio
import logging
import sys

from temporalio.client import Client
from temporalio.contrib.langsmith import LangSmithPlugin
from temporalio.contrib.pydantic import pydantic_data_converter
from temporalio.envconfig import ClientConfig
from temporalio.worker import Worker

from langsmith_tracing.basic.activities import call_openai
from langsmith_tracing.basic.workflows import BasicLLMWorkflow

interrupt_event = asyncio.Event()


async def main():
    logging.basicConfig(level=logging.INFO)

    # add_temporal_runs=True creates LangSmith runs for each Temporal
    # workflow/activity execution. False (default) only propagates context.
    add_temporal_runs = "--temporal-runs" in sys.argv

    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")

    client = await Client.connect(
        **config,
        data_converter=pydantic_data_converter,
    )

    plugin = LangSmithPlugin(
        project_name="langsmith-basic",
        add_temporal_runs=add_temporal_runs,
    )

    async with Worker(
        client,
        task_queue="langsmith-basic-task-queue",
        workflows=[BasicLLMWorkflow],
        activities=[call_openai],
        plugins=[plugin],
    ):
        label = "with" if add_temporal_runs else "without"
        print(f"Worker started ({label} Temporal runs in traces), ctrl+c to exit")
        await interrupt_event.wait()
        print("Shutting down")


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        interrupt_event.set()
        loop.run_until_complete(loop.shutdown_asyncgens())
