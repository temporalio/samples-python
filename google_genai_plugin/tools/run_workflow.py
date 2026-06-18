"""Start the tools workflow."""

# @@@SNIPSTART python-google-genai-tools-run-workflow
import asyncio
import os

from temporalio.client import Client

from google_genai_plugin.tools.workflow import ToolsWorkflow


async def main() -> None:
    client = await Client.connect(os.environ.get("TEMPORAL_ADDRESS", "localhost:7233"))

    result = await client.execute_workflow(
        ToolsWorkflow.run,
        "What's the weather in Tokyo, and what should I do there?",
        id="google-genai-tools",
        task_queue="google-genai-tools",
    )

    print(f"Result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
# @@@SNIPEND
