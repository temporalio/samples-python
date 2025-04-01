import asyncio
from dataclasses import dataclass
from datetime import timedelta
from typing import Optional

from temporalio import activity, workflow

from resource_locking.lock_manager_workflow import (
    LOCK_MANAGER_WORKFLOW_ID,
    AcquireRequest,
    AssignedResource,
    HandoffRequest,
    ReleaseRequest,
)


@dataclass
class UseResourceActivityInput:
    resource: str
    iteration: str


@activity.defn
async def use_resource(input: UseResourceActivityInput) -> None:
    info = activity.info()
    activity.logger.info(
        f"{info.workflow_id} starts using {input.resource} the {input.iteration} time"
    )
    await asyncio.sleep(3)
    activity.logger.info(
        f"{info.workflow_id} done using {input.resource} the {input.iteration} time"
    )


@dataclass
class ResourceLockingWorkflowInput:
    # If set, this workflow will fail after the "first", "second", or "third" activity.
    iteration_to_fail_after: Optional[str]

    # If True, this workflow will continue as new after the third activity. The next iteration will run three more
    # activities, but will not continue as new. This lets us exercise the handoff logic.
    should_continue_as_new: bool

    # Used to transfer resource ownership between iterations during continue_as_new
    already_owned_resource: Optional[str]


class FailWorkflowException(Exception):
    pass


# Wait this long for a resource before giving up
MAX_RESOURCE_WAIT_TIME = timedelta(minutes=5)


@workflow.defn(failure_exception_types=[FailWorkflowException])
class ResourceLockingWorkflow:
    def __init__(self):
        self.assigned_resource: Optional[str] = None

    @workflow.signal(name="assign_resource")
    def handle_assign_resource(self, input: AssignedResource):
        self.assigned_resource = input.resource

    @workflow.run
    async def run(self, input: ResourceLockingWorkflowInput):
        workflow.info()
        if has_timeout(workflow.info().run_timeout):
            # See "locking" comment below for rationale
            raise FailWorkflowException(
                f"ResourceLockingWorkflow cannot have a run_timeout (found {workflow.info().run_timeout})"
            )
        if has_timeout(workflow.info().execution_timeout):
            raise FailWorkflowException(
                f"ResourceLockingWorkflow cannot have an execution_timeout (found {workflow.info().execution_timeout})"
            )

        sem_handle = workflow.get_external_workflow_handle(LOCK_MANAGER_WORKFLOW_ID)

        info = workflow.info()
        if input.already_owned_resource is None:
            await sem_handle.signal(
                "acquire_resource", AcquireRequest(info.workflow_id, info.run_id)
            )
        else:
            # If we continued as new, we already have a resource. We need to transfer ownership from our predecessor to
            # ourselves.
            await sem_handle.signal(
                "handoff_resource",
                HandoffRequest(
                    input.already_owned_resource,
                    info.workflow_id,
                    info.continued_run_id,
                    info.run_id,
                ),
            )

        # Both branches above should cause us to receive an "assign_resource" signal.
        await workflow.wait_condition(
            lambda: self.assigned_resource is not None, timeout=MAX_RESOURCE_WAIT_TIME
        )
        if self.assigned_resource is None:
            raise FailWorkflowException(
                f"No resource was assigned after {MAX_RESOURCE_WAIT_TIME}"
            )

        # From this point forward, we own the resource. Note that this is a lock, not a lease! Our finally block will
        # release the resource if an activity fails. This is why we asserted the lack of workflow-level timeouts
        # above - the finally block wouldn't run if there was a timeout.
        try:
            for iteration in ["first", "second", "third"]:
                await workflow.execute_activity(
                    use_resource,
                    UseResourceActivityInput(self.assigned_resource, iteration),
                    start_to_close_timeout=timedelta(seconds=10),
                )

                if iteration == input.iteration_to_fail_after:
                    workflow.logger.info(
                        f"Failing after iteration {input.iteration_to_fail_after}"
                    )
                    raise FailWorkflowException()

            if input.should_continue_as_new:
                next_input = ResourceLockingWorkflowInput(
                    iteration_to_fail_after=input.iteration_to_fail_after,
                    should_continue_as_new=False,
                    already_owned_resource=self.assigned_resource,
                )
                workflow.continue_as_new(next_input)
        finally:
            # Only release the resource if we didn't continue-as-new. workflow.continue_as_new raises to halt workflow
            # execution, but this code in this finally block will still run. It wouldn't successfully send the signal...
            # the if statement just avoids some warnings in the log.
            if not input.should_continue_as_new:
                await sem_handle.signal(
                    "release_resource",
                    ReleaseRequest(
                        self.assigned_resource, info.workflow_id, info.run_id
                    ),
                )


def has_timeout(timeout: Optional[timedelta]) -> bool:
    # After continue_as_new, timeouts are 0, even if they were None before continue_as_new (and were not set in the
    # continue_as_new call).
    return timeout is not None and timeout > timedelta(0)
