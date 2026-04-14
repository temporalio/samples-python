"""Start the continue-as-new pipeline workflow (Functional API)."""

import asyncio
from datetime import timedelta

from temporalio.client import Client

from langgraph_plugin.functional_api.continue_as_new.workflow import (
    PipelineFunctionalWorkflow,
    PipelineInput,
)


async def main() -> None:
    client = await Client.connect("localhost:7233")

    result = await client.execute_workflow(
        PipelineFunctionalWorkflow.run,
        PipelineInput(data=10),
        id="pipeline-functional-workflow",
        task_queue="langgraph-pipeline-functional",
        execution_timeout=timedelta(seconds=60),
    )

    # 10*2=20 -> 20+50=70 -> 70*3=210
    print(f"Pipeline result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
