import asyncio
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Optional

from temporalio import activity, workflow

from resource_pool.pool_client import ResourcePoolClient
from resource_pool.shared import DetachedResource


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
class ResourceUserWorkflowInput:
    # The id of the resource pool workflow to request a resource from
    resource_pool_workflow_id: str

    # If set, this workflow will fail after the "first" or "second" activity.
    iteration_to_fail_after: Optional[str]

    # If True, this workflow will continue as new after the last activity. The next iteration will run more activities,
    # but will not continue as new.
    should_continue_as_new: bool

    # Used to transfer resource ownership between iterations during continue_as_new
    already_acquired_resource: Optional[DetachedResource] = field(default=None)


class FailWorkflowException(Exception):
    pass


# Wait this long for a resource before giving up
MAX_RESOURCE_WAIT_TIME = timedelta(minutes=5)


@workflow.defn(failure_exception_types=[FailWorkflowException])
class ResourceUserWorkflow:
    @workflow.run
    async def run(self, input: ResourceUserWorkflowInput) -> None:
        pool_client = ResourcePoolClient(input.resource_pool_workflow_id)

        async with pool_client.acquire_resource(
            reattach=input.already_acquired_resource
        ) as acquired_resource:
            for iteration in ["first", "second"]:
                await workflow.execute_activity(
                    use_resource,
                    UseResourceActivityInput(acquired_resource.resource, iteration),
                    start_to_close_timeout=timedelta(seconds=10),
                )

                if iteration == input.iteration_to_fail_after:
                    workflow.logger.info(
                        f"Failing after iteration {input.iteration_to_fail_after}"
                    )
                    raise FailWorkflowException()

            # This workflow only continues as new so it can demonstrate how to pass acquired resources across
            # iterations. Ordinarily, such a short workflow would not use continue as new.
            if input.should_continue_as_new:
                detached_resource = acquired_resource.detach()

                next_input = ResourceUserWorkflowInput(
                    resource_pool_workflow_id=input.resource_pool_workflow_id,
                    iteration_to_fail_after=input.iteration_to_fail_after,
                    should_continue_as_new=False,
                    already_acquired_resource=detached_resource,
                )

                workflow.continue_as_new(next_input)
