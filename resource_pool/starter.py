import asyncio
from typing import Any

from temporalio.client import Client, WorkflowFailureError, WorkflowHandle
from temporalio.common import WorkflowIDConflictPolicy

from resource_pool.resource_pool_workflow import (
    ResourcePoolWorkflow,
    ResourcePoolWorkflowInput,
)
from resource_pool.resource_user_workflow import (
    ResourceUserWorkflow,
    ResourceUserWorkflowInput,
)
from resource_pool.shared import RESOURCE_POOL_WORKFLOW_ID


async def main() -> None:
    # Connect client
    client = await Client.connect("localhost:7233")

    # Start the ResourceUserWorkflows
    resource_user_handles: list[WorkflowHandle[Any, Any]] = []
    for i in range(0, 4):
        input = ResourceUserWorkflowInput(
            iteration_to_fail_after=None,
            should_continue_as_new=False,
        )
        if i == 0:
            input.should_continue_as_new = True
        if i == 1:
            input.iteration_to_fail_after = "first"

        handle = await client.start_workflow(
            workflow=ResourceUserWorkflow.run,
            arg=input,
            id=f"resource-user-workflow-{i}",
            task_queue="default",
        )
        resource_user_handles.append(handle)

    # Add some resources
    resource_pool_handle = await client.start_workflow(
        workflow=ResourcePoolWorkflow.run,
        arg=ResourcePoolWorkflowInput(
            resources={},
            waiters=[],
        ),
        id=RESOURCE_POOL_WORKFLOW_ID,
        task_queue="default",
        id_conflict_policy=WorkflowIDConflictPolicy.USE_EXISTING,
        start_signal="add_resources",
        start_signal_args=[["resource_a", "resource_b"]],
    )

    for handle in resource_user_handles:
        try:
            await handle.result()
        except WorkflowFailureError:
            pass

    # Clean up after ourselves. In the real world, the resource pool workflow would run forever.
    await resource_pool_handle.terminate()


if __name__ == "__main__":
    asyncio.run(main())
