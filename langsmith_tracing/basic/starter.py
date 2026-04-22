"""Starter for the basic LangSmith sample."""

import asyncio
import sys

from langsmith import traceable
from temporalio.client import Client
from temporalio.contrib.langsmith import LangSmithPlugin
from temporalio.envconfig import ClientConfig

from langsmith_tracing.basic.workflows import BasicLLMWorkflow

PROJECT_NAME = "langsmith-basic"


async def main():
    add_temporal_runs = "--add-temporal-runs" in sys.argv

    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")

    plugin = LangSmithPlugin(
        project_name=PROJECT_NAME,
        add_temporal_runs=add_temporal_runs,
    )

    client = await Client.connect(
        **config,
        plugins=[plugin],
    )

    @traceable(
        name="Basic LLM Request",
        run_type="chain",
        # CRITICAL: Client-side @traceable runs outside the LangSmithPlugin's scope.
        # Make sure client-side traces use the same project_name as what is given to
        # # the plugin.
        project_name=PROJECT_NAME,
        tags=["client-side"],
    )
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
