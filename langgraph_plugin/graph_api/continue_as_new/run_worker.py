"""Worker for the continue-as-new pipeline (Graph API)."""

import asyncio
import os

from temporalio.client import Client
from temporalio.contrib.langgraph import LangGraphPlugin
from temporalio.worker import Worker

from langgraph_plugin.graph_api.continue_as_new.workflow import (
    PipelineWorkflow,
    pipeline_graph,
)


async def main() -> None:
    client = await Client.connect(os.environ.get("TEMPORAL_ADDRESS", "localhost:7233"))
    plugin = LangGraphPlugin(graphs=[pipeline_graph])

    worker = Worker(
        client,
        task_queue="langgraph-pipeline",
        workflows=[PipelineWorkflow],
        plugins=[plugin],
    )
    print("Worker started. Ctrl+C to exit.")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
