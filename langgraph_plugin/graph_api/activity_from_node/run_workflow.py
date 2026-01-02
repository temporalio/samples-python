"""Run the Activity from Node workflow.

Starts a workflow execution and waits for the result.
"""

import asyncio
import uuid

from temporalio.client import Client
from temporalio.envconfig import ClientConfig

from langgraph_plugin.graph_api.activity_from_node.workflow import ActivityFromNodeWorkflow


async def main() -> None:
    # Connect to Temporal
    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")
    client = await Client.connect(**config)

    # Run the workflow
    result = await client.execute_workflow(
        ActivityFromNodeWorkflow.run,
        "Hello from LangGraph",
        id=f"activity-from-node-{uuid.uuid4()}",
        task_queue="langgraph-activity-from-node",
    )

    print(f"Result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
