"""Worker for the Plan-and-Execute Agent sample.

Starts a Temporal worker that can execute PlanAndExecuteWorkflow.
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

from langgraph_samples.plan_and_execute.graph import (
    build_plan_and_execute_graph,
)
from langgraph_samples.plan_and_execute.workflow import (
    PlanAndExecuteWorkflow,
)


async def main() -> None:
    # Create the plugin with the plan-and-execute graph registered
    plugin = LangGraphPlugin(
        graphs={"plan_and_execute": build_plan_and_execute_graph},
    )

    # Connect to Temporal with the plugin
    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")
    client = await Client.connect(**config, plugins=[plugin])

    # Create and run the worker
    worker = Worker(
        client,
        task_queue="langgraph-plan-execute",
        workflows=[PlanAndExecuteWorkflow],
    )

    print("Plan-and-Execute Agent worker started. Ctrl+C to exit.")
    print("Make sure OPENAI_API_KEY is set in your environment.")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
