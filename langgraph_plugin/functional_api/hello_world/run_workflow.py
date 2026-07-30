"""Start the hello world workflow (Functional API)."""

import asyncio
import os

from temporalio.client import Client

from langgraph_plugin.functional_api.hello_world.workflow import (
    HelloWorldFunctionalWorkflow,
)


async def main() -> None:
    client = await Client.connect(os.environ.get("TEMPORAL_ADDRESS", "localhost:7233"))

    result = await client.execute_workflow(
        HelloWorldFunctionalWorkflow.run,
        "Hello, Temporal + LangGraph!",
        id="hello-world-functional-workflow",
        task_queue="langgraph-hello-world-functional",
    )

    print(f"Result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
