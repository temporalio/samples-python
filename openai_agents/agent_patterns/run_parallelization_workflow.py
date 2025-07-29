import asyncio

from temporalio.client import Client
from temporalio.contrib.openai_agents import OpenAIAgentsPlugin

from openai_agents.agent_patterns.workflows.parallelization_workflow import (
    ParallelizationWorkflow,
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
        ParallelizationWorkflow.run,
        "Hello, world! How are you today?",
        id="parallelization-workflow-example",
        task_queue="openai-agents-patterns-task-queue",
    )
    print(f"Result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
