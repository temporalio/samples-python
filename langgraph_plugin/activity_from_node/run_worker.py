"""Worker for the Activity from Node example.

Starts a Temporal worker that can execute ActivityFromNodeWorkflow.
"""

import asyncio

from temporalio.client import Client
from temporalio.contrib.langgraph import LangGraphPlugin
from temporalio.envconfig import ClientConfig
from temporalio.worker import Worker

from langgraph_plugin.activity_from_node.activities import enrich_data, validate_data
from langgraph_plugin.activity_from_node.graph import build_activity_from_node_graph
from langgraph_plugin.activity_from_node.workflow import ActivityFromNodeWorkflow


async def main() -> None:
    # Create the plugin with our graph registered
    plugin = LangGraphPlugin(
        graphs={"activity_from_node_graph": build_activity_from_node_graph},
    )

    # Connect to Temporal with the plugin
    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")
    client = await Client.connect(**config, plugins=[plugin])

    # Create and run the worker
    # Note: We register our custom activities alongside LangGraph's auto-registered ones
    worker = Worker(
        client,
        task_queue="langgraph-activity-from-node",
        workflows=[ActivityFromNodeWorkflow],
        activities=[validate_data, enrich_data],
    )

    print("Worker started. Ctrl+C to exit.")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
