"""Starter for the basic LangSmith sample."""

import asyncio

from temporalio.client import Client
from temporalio.contrib.langsmith import LangSmithPlugin
from temporalio.contrib.pydantic import pydantic_data_converter
from temporalio.envconfig import ClientConfig

from langsmith_tracing.basic.workflows import BasicLLMWorkflow


async def main():
    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")

    plugin = LangSmithPlugin(project_name="langsmith-basic")

    client = await Client.connect(
        **config,
        data_converter=pydantic_data_converter,
        plugins=[plugin],
    )

    result = await client.execute_workflow(
        BasicLLMWorkflow.run,
        "What is Temporal?",
        id="langsmith-basic-workflow-id",
        task_queue="langsmith-basic-task-queue",
    )
    print(f"Workflow result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
