import asyncio
from dataclasses import dataclass
from datetime import timedelta
from typing import Optional

from temporalio import activity, workflow
from temporalio.client import Client

from resource_locking.sem_workflow import AssignedResource, SEMAPHORE_WORKFLOW_ID, \
    ReleaseRequest, AcquireRequest, SemaphoreWorkflowInput, SEMAPHORE_WORKFLOW_TYPE


@dataclass
class LoadActivityInput:
    resource: str
    iteration: str

@activity.defn
async def load(input: LoadActivityInput) -> None:
    workflow_id = activity.info().workflow_id
    print(f"Workflow {workflow_id} starts using {input.resource} the {input.iteration} time")
    await asyncio.sleep(5)
    print(f"Workflow {workflow_id} finishes using {input.resource} the {input.iteration} time")

@dataclass
class LoadWorkflowInput:
    iteration_to_fail_after: Optional[str]

class FailWorkflowException(Exception):
    pass

MAX_RESOURCE_WAIT_TIME = timedelta(minutes=5)

@workflow.defn(
  failure_exception_types=[FailWorkflowException]
)
class LoadWorkflow:

    def __init__(self):
        self.assigned_resource = None

    @workflow.signal(name="assign_resource")
    def handle_assign_resource(self, input: AssignedResource):
        self.assigned_resource = input.resource

    @workflow.run
    async def run(self, input: LoadWorkflowInput):
        if workflow.info().run_timeout is not None:
            # See "locking" comment below for rationale
            raise FailWorkflowException(f"LoadWorkflow cannot have a run_timeout")
        if workflow.info().execution_timeout is not None:
            raise FailWorkflowException(f"LoadWorkflow cannot have an execution_timeout")

        sem_handle = workflow.get_external_workflow_handle(SEMAPHORE_WORKFLOW_ID)

        # Ask for a resource...
        info = workflow.info()
        await sem_handle.signal("acquire_resource", AcquireRequest(info.workflow_id, info.run_id))

        # ...and wait for the answer
        await workflow.wait_condition(lambda: self.assigned_resource is not None, timeout=MAX_RESOURCE_WAIT_TIME)
        if self.assigned_resource is None:
            raise FailWorkflowException(f"No resource was assigned after {MAX_RESOURCE_WAIT_TIME}")

        # From this point forward, we own the resource. Note that this is a lock, not a lease! Our finally block needs
        # to run to free up the resource if an activity fails. This is why we asserted the lack of workflow-level
        # timeouts above - they would prevent the finally block from running if there was a timeout.
        try:
            for iteration in ["first", "second", "third"]:
                await workflow.execute_activity(
                    load,
                    LoadActivityInput(self.assigned_resource, iteration),
                    start_to_close_timeout=timedelta(seconds=10),
                )

                if iteration == input.iteration_to_fail_after:
                    workflow.logger.info(f"Failing after iteration {input.iteration_to_fail_after}")
                    raise FailWorkflowException()
        finally:
            await sem_handle.signal("release_resource", ReleaseRequest(self.assigned_resource, info.workflow_id, info.run_id))