import asyncio
import uuid

from temporalio.client import Client
from temporalio.contrib.openai_agents.open_ai_data_converter import (
    open_ai_data_converter,
)

from nexus_openai_agents.tools_workflow import ToolsWorkflow

async def main():
    # Create client connected to server at the given address
    client = await Client.connect(
        "localhost:7233",
        data_converter=open_ai_data_converter,
    )

    # Execute a workflow
    result = await client.execute_workflow(
        ToolsWorkflow.run,
        "What is the weather in Berlin?",
        id=f"tools-workflow-{uuid.uuid4()}",
        task_queue="tools-task-queue",
    )

    print(f"Result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
