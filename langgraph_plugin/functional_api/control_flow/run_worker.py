"""Worker for the control flow pipeline (Functional API)."""

import asyncio
import os

from temporalio.client import Client
from temporalio.contrib.langgraph import LangGraphPlugin
from temporalio.worker import Worker

from langgraph_plugin.functional_api.control_flow.workflow import (
    ControlFlowWorkflow,
    activity_options,
    all_tasks,
)


async def main() -> None:
    client = await Client.connect(os.environ.get("TEMPORAL_ADDRESS", "localhost:7233"))
    plugin = LangGraphPlugin(
        tasks=all_tasks,
        activity_options=activity_options,
    )

    worker = Worker(
        client,
        task_queue="langgraph-control-flow",
        workflows=[ControlFlowWorkflow],
        plugins=[plugin],
    )
    print("Worker started. Ctrl+C to exit.")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
