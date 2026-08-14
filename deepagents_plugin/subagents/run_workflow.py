"""Start the subagents workflow and print the coordinator's synthesized answer."""

import asyncio
import os

from temporalio.client import Client

from deepagents_plugin.subagents.workflow import SubagentsWorkflow


async def main() -> None:
    client = await Client.connect(os.environ.get("TEMPORAL_ADDRESS", "localhost:7233"))

    result = await client.execute_workflow(
        SubagentsWorkflow.run,
        "Investigate how Temporal handles workflow retries and summarize it.",
        id="deepagents-subagents",
        task_queue="deepagents-subagents",
    )

    print(f"Result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
