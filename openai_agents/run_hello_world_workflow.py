import asyncio

from temporalio.client import Client

from openai_agents.workflows.research_bot_workflow import ResearchWorkflow
from openai_agents.workflows.hello_world_workflow import HelloWorldAgent
from temporalio.contrib.openai_agents import Plugin

async def main():
    # Create client connected to server at the given address
    client = await Client.connect(
        "localhost:7233",
        plugins=[Plugin()],
    )

    # Execute a workflow
    result = await client.execute_workflow(
        HelloWorldAgent.run,
        "Tell me about recursion in programming.",
        id="my-workflow-id",
        task_queue="openai-agents-task-queue",
    )
    print(f"Result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
