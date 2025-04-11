import asyncio
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Callable, Optional

from temporalio import activity, workflow

from resource_locking.resource_allocator import ResourceAllocator
from resource_locking.shared import (
    LOCK_MANAGER_WORKFLOW_ID,
    AcquiredResource,
    AcquireRequest,
    AcquireResponse,
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
    already_acquired_resource: Optional[AcquiredResource] = field(default=None)


class FailWorkflowException(Exception):
    pass


# Wait this long for a resource before giving up
MAX_RESOURCE_WAIT_TIME = timedelta(minutes=5)


@workflow.defn(failure_exception_types=[FailWorkflowException])
class ResourceLockingWorkflow:
    @workflow.run
    async def run(self, input: ResourceLockingWorkflowInput):
        async with ResourceAllocator.acquire_resource(
            already_acquired_resource=input.already_acquired_resource
        ) as resource:
            for iteration in ["first", "second"]:
                await workflow.execute_activity(
                    use_resource,
                    UseResourceActivityInput(resource.resource, iteration),
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
                    already_acquired_resource=resource,
                )

                # By default, ResourceAllocator will release the resource when we return. We want to hold the resource
                # across continue-as-new for the sake of demonstration.b
                resource.autorelease = False

                workflow.continue_as_new(next_input)
