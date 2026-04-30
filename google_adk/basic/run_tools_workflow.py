import asyncio

from temporalio.client import Client
from temporalio.contrib.google_adk_agents import GoogleAdkPlugin

from google_adk.basic.workflows.tools_workflow import ToolsWorkflow


async def main():
    client = await Client.connect(
        "localhost:7233",
        plugins=[GoogleAdkPlugin()],
    )

    result = await client.execute_workflow(
        ToolsWorkflow.run,
        "What is the weather in Tokyo?",
        id="google-adk-tools-workflow",
        task_queue="google-adk-basic-task-queue",
    )
    print(f"Result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
