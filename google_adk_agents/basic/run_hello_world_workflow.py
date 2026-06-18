import asyncio

from temporalio.client import Client
from temporalio.contrib.google_adk_agents import GoogleAdkPlugin

from google_adk_agents.basic.workflows.hello_world_workflow import (
    HelloWorldAgentWorkflow,
)


async def main():
    client = await Client.connect("localhost:7233", plugins=[GoogleAdkPlugin()])

    result = await client.execute_workflow(
        HelloWorldAgentWorkflow.run,
        "Tell me about recursion in programming.",
        id="google-adk-agents-basic-workflow-id",
        task_queue="google-adk-agents-basic",
    )
    print(f"Result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
