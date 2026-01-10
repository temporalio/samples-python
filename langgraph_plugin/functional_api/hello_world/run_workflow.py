"""Execute the Hello World LangGraph Functional API workflow.

Connects to Temporal and starts the HelloWorldWorkflow.
"""

import asyncio

from temporalio.client import Client
from temporalio.envconfig import ClientConfig

from langgraph_plugin.functional_api.hello_world.workflow import HelloWorldWorkflow


async def main() -> None:
    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")
    client = await Client.connect(**config)

    # Execute the workflow
    result = await client.execute_workflow(
        HelloWorldWorkflow.run,
        "Hello, Temporal!",
        id="hello-world-functional-workflow",
        task_queue="langgraph-functional-hello-world",
    )

    print(f"Result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
