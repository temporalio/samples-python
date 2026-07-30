"""Start the hello world workflow (Graph API)."""

import asyncio
import os

from temporalio.client import Client

from langgraph_plugin.graph_api.hello_world.workflow import HelloWorldWorkflow


async def main() -> None:
    client = await Client.connect(os.environ.get("TEMPORAL_ADDRESS", "localhost:7233"))

    result = await client.execute_workflow(
        HelloWorldWorkflow.run,
        "Hello, Temporal + LangGraph!",
        id="hello-world-workflow",
        task_queue="langgraph-hello-world",
    )

    print(f"Result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
