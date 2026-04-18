"""Worker for the LangSmith tracing sample (Graph API).

Requires ANTHROPIC_API_KEY and LANGCHAIN_API_KEY environment variables.
"""

import asyncio
import os

from temporalio.client import Client
from temporalio.contrib.langgraph import LangGraphPlugin
from temporalio.contrib.langsmith import LangSmithPlugin
from temporalio.worker import Worker

from langgraph_plugin.graph_api.langsmith_tracing.workflow import (
    ChatWorkflow,
    chat_graph,
)


async def main() -> None:
    client = await Client.connect(
        os.environ.get("TEMPORAL_ADDRESS", "localhost:7233"),
        plugins=[LangSmithPlugin(add_temporal_runs=True)],
    )

    worker = Worker(
        client,
        task_queue="langgraph-langsmith",
        workflows=[ChatWorkflow],
        plugins=[LangGraphPlugin(graphs=[chat_graph])],
    )
    print("Worker started. Ctrl+C to exit.")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
