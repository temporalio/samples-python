import asyncio

from temporalio.client import Client
from temporalio.contrib.google_adk_agents import GoogleAdkPlugin

from google_adk.basic.workflows.hello_world_workflow import HelloWorldWorkflow


async def main():
    client = await Client.connect(
        "localhost:7233",
        plugins=[GoogleAdkPlugin()],
    )

    result = await client.execute_workflow(
        HelloWorldWorkflow.run,
        "Tell me about recursion in programming.",
        id="google-adk-hello-world",
        task_queue="google-adk-basic-task-queue",
    )
    print(f"Result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
