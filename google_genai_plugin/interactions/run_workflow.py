"""Start the interactions workflow."""

import asyncio
import os

from temporalio.client import Client

from google_genai_plugin.interactions.workflow import InteractionsWorkflow


async def main() -> None:
    client = await Client.connect(os.environ.get("TEMPORAL_ADDRESS", "localhost:7233"))

    result = await client.execute_workflow(
        InteractionsWorkflow.run,
        "What is durable execution?",
        id="google-genai-interactions",
        task_queue="google-genai-interactions",
    )

    print(f"Result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
