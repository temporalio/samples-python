"""Worker for the Supervisor Multi-Agent sample.

Starts a Temporal worker that can execute SupervisorWorkflow.
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

from langgraph_samples.supervisor.graph import build_supervisor_graph
from langgraph_samples.supervisor.workflow import SupervisorWorkflow


async def main() -> None:
    # Create the plugin with the supervisor graph registered
    plugin = LangGraphPlugin(
        graphs={"supervisor": build_supervisor_graph},
    )

    # Connect to Temporal with the plugin
    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")
    client = await Client.connect(**config, plugins=[plugin])

    # Create and run the worker
    # Note: Activities (LLM calls, tool executions, agent handoffs) are automatically registered
    worker = Worker(
        client,
        task_queue="langgraph-supervisor",
        workflows=[SupervisorWorkflow],
    )

    print("Supervisor Multi-Agent worker started. Ctrl+C to exit.")
    print("Make sure OPENAI_API_KEY is set in your environment.")
    print()
    print("This worker handles:")
    print("  - Supervisor: Coordinates and routes tasks")
    print("  - Researcher: Web search and information gathering")
    print("  - Writer: Content creation and summarization")
    print("  - Analyst: Calculations and data analysis")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
