"""Start the continue-as-new pipeline workflow (Graph API)."""

import asyncio
import os
from datetime import timedelta

from temporalio.client import Client

from langgraph_plugin.graph_api.continue_as_new.workflow import (
    PipelineInput,
    PipelineWorkflow,
)


async def main() -> None:
    client = await Client.connect(os.environ.get("TEMPORAL_ADDRESS", "localhost:7233"))

    result = await client.execute_workflow(
        PipelineWorkflow.run,
        PipelineInput(data=10),
        id="pipeline-workflow",
        task_queue="langgraph-pipeline",
        execution_timeout=timedelta(seconds=60),
    )

    # 10*2=20 -> 20+50=70 -> 70*3=210
    print(f"Pipeline result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
