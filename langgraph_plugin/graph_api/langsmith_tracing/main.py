"""Run the LangSmith tracing chat sample (Graph API).

Single-process driver: starts a Worker, executes the Workflow once, prints
the result, then shuts down. Requires ANTHROPIC_API_KEY and LANGCHAIN_API_KEY.
"""

import asyncio
import os

from temporalio.client import Client
from temporalio.contrib.langgraph import LangGraphPlugin
from temporalio.contrib.langsmith import LangSmithPlugin
from temporalio.worker import Worker

from langgraph_plugin.graph_api.langsmith_tracing.workflow import (
    ChatWorkflow,
    make_chat_graph,
)


async def main() -> None:
    client = await Client.connect(
        os.environ.get("TEMPORAL_ADDRESS", "localhost:7233"),
        plugins=[LangSmithPlugin(add_temporal_runs=True)],
    )

    async with Worker(
        client,
        task_queue="langgraph-langsmith",
        workflows=[ChatWorkflow],
        plugins=[LangGraphPlugin(graphs={"chat": make_chat_graph()})],
    ):
        result = await client.execute_workflow(
            ChatWorkflow.run,
            "What is the meaning of life?",
            id="langsmith-chat-workflow",
            task_queue="langgraph-langsmith",
        )
        print(f"Response: {result}")


if __name__ == "__main__":
    asyncio.run(main())
