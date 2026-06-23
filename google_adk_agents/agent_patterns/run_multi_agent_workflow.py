import asyncio

from temporalio.client import Client
from temporalio.contrib.google_adk_agents import GoogleAdkPlugin

from google_adk_agents.agent_patterns.workflows.multi_agent_workflow import (
    MultiAgentWorkflow,
)


async def main():
    client = await Client.connect("localhost:7233", plugins=[GoogleAdkPlugin()])

    result = await client.execute_workflow(
        MultiAgentWorkflow.run,
        "the ocean",
        id="google-adk-agents-agent-patterns-workflow-id",
        task_queue="google-adk-agents-agent-patterns",
    )
    print(f"Result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
