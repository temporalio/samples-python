"""Worker for the ReAct agent (Functional API)."""

import asyncio

from temporalio.client import Client
from temporalio.contrib.langgraph import LangGraphPlugin
from temporalio.worker import Worker

from langgraph_plugin.functional_api.react_agent.workflow import (
    ReactAgentFunctionalWorkflow,
    activity_options,
    all_tasks,
    react_agent_entrypoint,
)


async def main() -> None:
    client = await Client.connect("localhost:7233")
    plugin = LangGraphPlugin(
        entrypoints={"react-agent": react_agent_entrypoint},
        tasks=all_tasks,
        activity_options=activity_options,
    )

    worker = Worker(
        client,
        task_queue="langgraph-react-agent-functional",
        workflows=[ReactAgentFunctionalWorkflow],
        plugins=[plugin],
    )
    print("Worker started. Ctrl+C to exit.")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
