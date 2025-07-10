import asyncio

from temporalio.client import Client

from openai_agents.workflows.tools_workflow import ToolsWorkflow
from temporalio.contrib.openai_agents import Plugin


async def main():
    # Create client connected to server at the given address
    client = await Client.connect(
        "localhost:7233",
        plugins=[Plugin()],
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
