"""Execute the Hello World LangGraph workflow.

Connects to Temporal and starts the HelloWorldWorkflow.
Note: The graph is only needed by the worker, not by the workflow starter.
"""

import asyncio

from temporalio.client import Client
from temporalio.envconfig import ClientConfig

from langgraph_samples.hello_world.workflow import HelloWorldWorkflow


async def main() -> None:
    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")
    client = await Client.connect(**config)

    # Execute the workflow
    result = await client.execute_workflow(
        HelloWorldWorkflow.run,
        "Hello, Temporal!",
        id="hello-world-workflow",
        task_queue="langgraph-hello-world",
    )

    print(f"Result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
