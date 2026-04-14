"""Worker for the ReAct agent (Graph API)."""

import asyncio

from temporalio.client import Client
from temporalio.contrib.langgraph import LangGraphPlugin
from temporalio.worker import Worker

from langgraph_plugin.graph_api.react_agent.workflow import (
    ReactAgentWorkflow,
    build_graph,
)


async def main() -> None:
    client = await Client.connect("localhost:7233")
    plugin = LangGraphPlugin(graphs={"react-agent": build_graph()})

    worker = Worker(
        client,
        task_queue="langgraph-react-agent",
        workflows=[ReactAgentWorkflow],
        plugins=[plugin],
    )
    print("Worker started. Ctrl+C to exit.")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
