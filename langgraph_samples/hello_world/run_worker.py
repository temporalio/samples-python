"""Worker for the Hello World LangGraph example.

Starts a Temporal worker that can execute HelloWorldWorkflow.
The LangGraphPlugin registers the graph and handles activity registration.
"""

import asyncio

from temporalio.client import Client
from temporalio.contrib.langgraph import LangGraphPlugin
from temporalio.envconfig import ClientConfig
from temporalio.worker import Worker

from langgraph_samples.hello_world.graph import build_hello_graph
from langgraph_samples.hello_world.workflow import HelloWorldWorkflow


async def main() -> None:
    # Create the plugin with our graph registered by name
    plugin = LangGraphPlugin(
        graphs={"hello_graph": build_hello_graph},
    )

    # Connect to Temporal with the plugin
    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")
    client = await Client.connect(**config, plugins=[plugin])

    # Create and run the worker
    # Note: Activities are automatically registered by the plugin
    worker = Worker(
        client,
        task_queue="langgraph-hello-world",
        workflows=[HelloWorldWorkflow],
    )

    print("Worker started. Ctrl+C to exit.")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
