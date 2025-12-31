"""Worker for the Deep Research Agent sample.

Starts a Temporal worker that can execute DeepResearchWorkflow.
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

from langgraph_plugin.deep_research.graph import build_deep_research_graph
from langgraph_plugin.deep_research.workflow import DeepResearchWorkflow


async def main() -> None:
    # Create the plugin with the deep research graph registered
    plugin = LangGraphPlugin(
        graphs={"deep_research": build_deep_research_graph},
    )

    # Connect to Temporal with the plugin
    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")
    client = await Client.connect(**config, plugins=[plugin])

    # Create and run the worker
    worker = Worker(
        client,
        task_queue="langgraph-deep-research",
        workflows=[DeepResearchWorkflow],
    )

    print("Deep Research Agent worker started. Ctrl+C to exit.")
    print("Make sure OPENAI_API_KEY is set in your environment.")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
