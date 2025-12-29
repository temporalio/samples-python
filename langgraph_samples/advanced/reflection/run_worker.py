"""Worker for the Reflection Agent sample.

Starts a Temporal worker that can execute ReflectionWorkflow.
The LangGraphPlugin registers the graph and handles activity registration.

Prerequisites:
    - Temporal server running locally
    - OPENAI_API_KEY environment variable set
"""

import asyncio

from temporalio.client import Client
from temporalio.contrib.langgraph import LangGraphPlugin
from temporalio.envconfig import ClientConfig
from temporalio.worker import Worker

from langgraph_samples.advanced.reflection.graph import build_reflection_graph
from langgraph_samples.advanced.reflection.workflow import ReflectionWorkflow


async def main() -> None:
    # Create the plugin with the reflection graph registered
    plugin = LangGraphPlugin(
        graphs={"reflection": build_reflection_graph},
    )

    # Connect to Temporal with the plugin
    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")
    client = await Client.connect(**config, plugins=[plugin])

    # Create and run the worker
    worker = Worker(
        client,
        task_queue="langgraph-reflection",
        workflows=[ReflectionWorkflow],
    )

    print("Reflection Agent worker started. Ctrl+C to exit.")
    print("Make sure OPENAI_API_KEY is set in your environment.")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
