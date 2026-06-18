"""Start the hello world workflow."""

# @@@SNIPSTART python-google-genai-hello-world-run-workflow
import asyncio
import os

from temporalio.client import Client

from google_genai_plugin.hello_world.workflow import HelloWorldWorkflow


async def main() -> None:
    client = await Client.connect(os.environ.get("TEMPORAL_ADDRESS", "localhost:7233"))

    result = await client.execute_workflow(
        HelloWorldWorkflow.run,
        "Write a haiku about durable execution.",
        id="google-genai-hello-world",
        task_queue="google-genai-hello-world",
    )

    print(f"Result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
# @@@SNIPEND
