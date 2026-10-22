"""Start the hello world workflow and print the agent's answer."""

# @@@SNIPSTART python-deepagents-hello-world-run-workflow
import asyncio
import os

from temporalio.client import Client

from deepagents_plugin.hello_world.workflow import HelloWorldAgent


async def main() -> None:
    client = await Client.connect(os.environ.get("TEMPORAL_ADDRESS", "localhost:7233"))

    result = await client.execute_workflow(
        HelloWorldAgent.run,
        "What is Temporal in one sentence?",
        id="deepagents-hello-world",
        task_queue="deepagents-hello-world",
    )

    print(f"Result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
# @@@SNIPEND
