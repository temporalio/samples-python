"""Execute the Continue-as-New workflow.

Runs the ContinueAsNewWorkflow which demonstrates task caching across
continue-as-new boundaries.
"""

import asyncio
import uuid

from temporalio.client import Client
from temporalio.envconfig import ClientConfig

from langgraph_plugin.functional_api.continue_as_new.workflow import (
    ContinueAsNewWorkflow,
    PipelineInput,
)


async def main() -> None:
    # Connect to Temporal
    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")
    client = await Client.connect(**config)

    # Start the workflow
    workflow_id = f"continue-as-new-{uuid.uuid4()}"
    print(f"Starting workflow: {workflow_id}")
    print("Input value: 10")
    print()
    print("Expected execution:")
    print("  Phase 1: step_1(10)=20, step_2(20)=25, step_3(25)=75")
    print("  [continue-as-new with checkpoint]")
    print("  Phase 2: step_1-3 CACHED, step_4(75)=65, step_5(65)=165")
    print()

    result = await client.execute_workflow(
        ContinueAsNewWorkflow.run,
        PipelineInput(value=10),
        id=workflow_id,
        task_queue="langgraph-functional-continue-as-new",
    )

    print(f"Result: {result}")
    print()
    print("Check the worker logs to verify:")
    print("  - step_1, step_2, step_3 logged only ONCE (in phase 1)")
    print("  - step_4, step_5 logged only in phase 2")
    print("  - No re-execution of cached tasks!")


if __name__ == "__main__":
    asyncio.run(main())
