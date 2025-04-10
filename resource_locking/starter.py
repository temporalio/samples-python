import asyncio
from typing import Any

from temporalio.client import Client, WorkflowFailureError, WorkflowHandle

from resource_locking.shared import LOCK_MANAGER_WORKFLOW_ID
from resource_locking.lock_manager_workflow import (
    LockManagerWorkflow,
    LockManagerWorkflowInput,
)
from resource_locking.resource_locking_workflow import (
    ResourceLockingWorkflow,
    ResourceLockingWorkflowInput,
)


async def main():
    # Connect client
    client = await Client.connect("localhost:7233")

    # Start the LockManagerWorkflow
    lock_manager_handle = await client.start_workflow(
        workflow=LockManagerWorkflow.run,
        arg=LockManagerWorkflowInput(
            {
                "resource_a": [],
                "resource_b": [],
            }
        ),
        id=LOCK_MANAGER_WORKFLOW_ID,
        task_queue="default",
    )

    # Start the ResourceLockingWorkflows
    resource_locking_handles: list[WorkflowHandle[Any, Any]] = []
    for i in range(0, 4):
        input = ResourceLockingWorkflowInput(
            iteration_to_fail_after=None,
            should_continue_as_new=False,
            already_assigned_resource=None,
        )
        if i == 0:
            input.should_continue_as_new = True
        if i == 1:
            input.iteration_to_fail_after = "first"

        resource_locking_handle = await client.start_workflow(
            workflow=ResourceLockingWorkflow.run,
            arg=input,
            id=f"resource-locking-workflow-{i}",
            task_queue="default",
        )
        resource_locking_handles.append(resource_locking_handle)

    for resource_locking_handle in resource_locking_handles:
        try:
            await resource_locking_handle.result()
        except WorkflowFailureError:
            pass

    # Clean up after ourselves. In the real world, the lock manager workflow would run forever.
    await lock_manager_handle.terminate()


if __name__ == "__main__":
    asyncio.run(main())
