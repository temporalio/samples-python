import asyncio
from typing import Any

from temporalio.client import Client, WorkflowHandle, WorkflowFailureError

from resource_locking.load_workflow import LoadWorkflow, LoadWorkflowInput
from resource_locking.sem_workflow import SemaphoreWorkflow, SemaphoreWorkflowInput, SEMAPHORE_WORKFLOW_ID


async def main():
    # Connect client
    client = await Client.connect("localhost:7233")

    # Run the semaphore workflow
    sem_handle = await client.start_workflow(
        workflow=SemaphoreWorkflow.run,
        arg=SemaphoreWorkflowInput({
            "resource_a": [],
            "resource_b": [],
        }),
        id=SEMAPHORE_WORKFLOW_ID,
        task_queue="default",
    )

    load_handles: list[WorkflowHandle[Any, Any]] = []
    for i in range(0, 4):
        input = LoadWorkflowInput(iteration_to_fail_after=None, should_continue_as_new=False, already_owned_resource=None)
        if i == 0:
            input.should_continue_as_new = True
        if i == 1:
            input.iteration_to_fail_after = "first"

        load_handle = await client.start_workflow(
            workflow=LoadWorkflow.run,
            arg=input,
            id=f"load-workflow-{i}",
            task_queue="default",
        )
        load_handles.append(load_handle)

    for load_handle in load_handles:
        try:
            await load_handle.result()
        except WorkflowFailureError:
            pass

    await sem_handle.terminate()


if __name__ == "__main__":
    asyncio.run(main())
