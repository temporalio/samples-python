"""Worker for the Hello World LangGraph Functional API example.

Starts a Temporal worker that can execute HelloWorldWorkflow.
The LangGraphFunctionalPlugin registers the entrypoint and handles activity registration.
"""

import asyncio

from temporalio.client import Client
from temporalio.contrib.langgraph import LangGraphFunctionalPlugin
from temporalio.envconfig import ClientConfig
from temporalio.worker import Worker

from langgraph_plugin.functional_api.hello_world.entrypoint import (
    hello_world_entrypoint,
)
from langgraph_plugin.functional_api.hello_world.workflow import HelloWorldWorkflow


async def main() -> None:
    # Create the plugin with our entrypoint registered by name
    plugin = LangGraphFunctionalPlugin(
        entrypoints={"hello_world_entrypoint": hello_world_entrypoint},
    )

    # Connect to Temporal with the plugin
    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")
    client = await Client.connect(**config, plugins=[plugin])

    # Create and run the worker
    # Note: The dynamic task activity is automatically registered by the plugin
    worker = Worker(
        client,
        task_queue="langgraph-functional-hello-world",
        workflows=[HelloWorldWorkflow],
    )

    print("Worker started. Ctrl+C to exit.")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
