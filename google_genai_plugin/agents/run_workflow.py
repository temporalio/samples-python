"""Start the agents workflow."""

import asyncio
import os

from temporalio.client import Client

from google_genai_plugin.agents.workflow import AgentsWorkflow


async def main() -> None:
    client = await Client.connect(os.environ.get("TEMPORAL_ADDRESS", "localhost:7233"))

    result = await client.execute_workflow(
        AgentsWorkflow.run,
        "samples-demo-agent",
        id="google-genai-agents",
        task_queue="google-genai-agents",
    )

    print(f"Result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
