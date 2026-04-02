"""Worker for the Agentic RAG sample.

Starts a Temporal worker that can execute AgenticRAGWorkflow.
The LangGraphPlugin registers the graph and handles activity registration.

Prerequisites:
    - Temporal server running locally
    - OPENAI_API_KEY environment variable set
"""

import asyncio
import logging
import sys

# Configure logging to see workflow.logger output
logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)

from temporalio.client import Client
from temporalio.contrib.langgraph import LangGraphPlugin
from temporalio.envconfig import ClientConfig
from temporalio.worker import Worker

from langgraph_plugin.graph_api.agentic_rag.graph import build_agentic_rag_graph
from langgraph_plugin.graph_api.agentic_rag.workflow import AgenticRAGWorkflow


async def main() -> None:
    # Create the plugin with the agentic RAG graph registered
    plugin = LangGraphPlugin(
        graphs={"agentic_rag": build_agentic_rag_graph},
    )

    # Connect to Temporal with the plugin
    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")
    client = await Client.connect(**config, plugins=[plugin])

    # Create and run the worker
    # Note: Activities (LLM calls, retrieval, grading) are automatically registered
    worker = Worker(
        client,
        task_queue="langgraph-agentic-rag",
        workflows=[AgenticRAGWorkflow],
    )

    print("Agentic RAG worker started. Ctrl+C to exit.")
    print("Make sure OPENAI_API_KEY is set in your environment.")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
