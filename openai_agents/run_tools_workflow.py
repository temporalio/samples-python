import asyncio

from temporalio.client import Client

from openai_agents.workflows.tools_workflow import ToolsWorkflow
from temporalio.contrib.pydantic import pydantic_data_converter


async def main():
    # Create client connected to server at the given address
    client = await Client.connect(
        "localhost:7233",
        data_converter=pydantic_data_converter,
    )

    # Execute a workflow
    result = await client.execute_workflow(
        ToolsWorkflow.run,
        "What is the weather in Tokio?",
        id="tools-workflow",
        task_queue="openai-agents-task-queue",
    )

    print(f"Result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
