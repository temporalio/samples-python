"""Worker for the human-in-the-loop chatbot (Graph API)."""

import asyncio

from temporalio.client import Client
from temporalio.contrib.langgraph import LangGraphPlugin
from temporalio.worker import Worker

from langgraph_plugin.graph_api.human_in_the_loop.workflow import (
    ChatbotWorkflow,
    build_graph,
)


async def main() -> None:
    client = await Client.connect("localhost:7233")
    plugin = LangGraphPlugin(graphs={"chatbot": build_graph()})

    worker = Worker(
        client,
        task_queue="langgraph-chatbot",
        workflows=[ChatbotWorkflow],
        plugins=[plugin],
    )
    print("Worker started. Ctrl+C to exit.")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
