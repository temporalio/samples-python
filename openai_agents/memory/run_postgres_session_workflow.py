import asyncio
import uuid

from temporalio.client import Client
from temporalio.contrib.openai_agents import OpenAIAgentsPlugin

from openai_agents.memory.workflows.postgres_session_workflow import (
    PostgresSessionWorkflow,
)


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
        PostgresSessionWorkflow.run,
        f"openai-session-workflow-{uuid.uuid4()}",
        id=f"openai-session-workflow-{uuid.uuid4()}",
        task_queue="openai-agents-memory-task-queue",
    )

    # Print the workflow output
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
