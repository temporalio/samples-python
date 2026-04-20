"""Starter for the basic LangSmith sample."""

import asyncio
import sys

from langsmith import traceable
from temporalio.client import Client
from temporalio.contrib.langsmith import LangSmithPlugin
from temporalio.contrib.pydantic import pydantic_data_converter
from temporalio.envconfig import ClientConfig

from langsmith_tracing.basic.workflows import BasicLLMWorkflow


async def main():
    add_temporal_runs = "--add-temporal-runs" in sys.argv

    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")

    plugin = LangSmithPlugin(
        project_name="langsmith-basic",
        add_temporal_runs=add_temporal_runs,
    )

    client = await Client.connect(
        **config,
        data_converter=pydantic_data_converter,
        plugins=[plugin],
    )

    # Client-side @traceable wraps the entire workflow call, creating a
    # root span in LangSmith that the workflow and activity traces nest under.
    @traceable(name="Basic LLM Request", run_type="chain", tags=["client-side"])
    async def run_workflow(prompt: str) -> str:
        return await client.execute_workflow(
            BasicLLMWorkflow.run,
            prompt,
            id="langsmith-basic-workflow-id",
            task_queue="langsmith-basic-task-queue",
        )

    result = await run_workflow("What is Temporal?")
    print(f"Workflow result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
