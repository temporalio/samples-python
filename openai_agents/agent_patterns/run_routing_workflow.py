import asyncio

from temporalio.client import Client
from temporalio.contrib.openai_agents import OpenAIAgentsPlugin

from openai_agents.agent_patterns.workflows.routing_workflow import RoutingWorkflow


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
        RoutingWorkflow.run,
        "Bonjour! Comment allez-vous aujourd'hui?",
        id="routing-workflow-example",
        task_queue="openai-agents-patterns-task-queue",
    )
    print(f"Result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
