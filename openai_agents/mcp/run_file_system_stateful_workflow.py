import asyncio
import os

from temporalio.client import Client
from temporalio.contrib.openai_agents import OpenAIAgentsPlugin

from openai_agents.mcp.workflows.file_system_stateful_workflow import FileSystemWorkflow

import uuid

async def main():
    # Create client connected to server at the given address
    client = await Client.connect(
        "localhost:7233",
        plugins=[
            OpenAIAgentsPlugin(),
        ],
    )

    # Execute a workflow
    result = await client.execute_workflow(
        FileSystemWorkflow.run,
        id=f"file-system-workflow-{uuid.uuid4()}",
        task_queue="openai-agents-mcp-stateful-task-queue",
    )

    print(f"Result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
