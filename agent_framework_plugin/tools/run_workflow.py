"""Start the tools workflow."""

import asyncio
import os

from temporalio.client import Client

from agent_framework_plugin.tools.workflow import ToolsWorkflow


async def main() -> None:
    client = await Client.connect(os.environ.get("TEMPORAL_ADDRESS", "localhost:7233"))

    result = await client.execute_workflow(
        ToolsWorkflow.run,
        (
            "Please do two things:\n"
            "1. Count the letter R's in 'strawberry'.\n"
            "2. Fetch the weather in San Francisco."
        ),
        id="agent-framework-tools",
        task_queue="agent-framework-tools",
    )

    print(f"Result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
