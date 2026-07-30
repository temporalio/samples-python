"""Start the hooks workflow."""

import asyncio
import os

from temporalio.client import Client

from strands_plugin.hooks.workflow import HooksWorkflow


async def main() -> None:
    client = await Client.connect(os.environ.get("TEMPORAL_ADDRESS", "localhost:7233"))

    fired = await client.execute_workflow(
        HooksWorkflow.run,
        "Echo 'hello' once.",
        id="strands-hooks",
        task_queue="strands-hooks",
    )

    print(f"Tools that fired AfterToolCallEvent: {fired}")


if __name__ == "__main__":
    asyncio.run(main())
