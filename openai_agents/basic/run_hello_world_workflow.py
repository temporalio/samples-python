import asyncio

from temporalio.client import Client
from temporalio.contrib.openai_agents import OpenAIAgentsPlugin

from openai_agents.basic.workflows.hello_world_workflow import HelloWorldAgent


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
        HelloWorldAgent.run,
        "Tell me about recursion in programming.",
        id="my-workflow-id",
        task_queue="openai-agents-basic-task-queue",
    )
    print(f"Result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
