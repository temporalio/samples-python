from contextlib import asynccontextmanager
from datetime import timedelta
from typing import AsyncGenerator, Optional

from temporalio import workflow

from resource_pool.shared import (
    AcquiredResource,
    AcquireRequest,
    AcquireResponse,
    DetachedResource,
)


# Use this class in workflow code that that needs to run on locked resources.
class ResourcePoolClient:
    def __init__(self, pool_workflow_id: str) -> None:
        self.pool_workflow_id = pool_workflow_id
        self.acquired_resources: list[AcquiredResource] = []

    async def send_acquire_signal(self) -> None:
        handle = workflow.get_external_workflow_handle(self.pool_workflow_id)
        await handle.signal(
            "acquire_resource", AcquireRequest(workflow.info().workflow_id)
        )

    async def send_release_signal(self, acquired_resource: AcquiredResource) -> None:
        handle = workflow.get_external_workflow_handle(self.pool_workflow_id)
        await handle.signal(
            "release_resource",
            AcquireResponse(
                resource=acquired_resource.resource,
                release_key=acquired_resource.release_key,
            ),
        )

    def lazy_register_signal_handler(self) -> None:
        if workflow.get_signal_handler("assign_resource") is None:
            workflow.set_signal_handler("assign_resource", self.assign_resource)

    def assign_resource(self, response: AcquireResponse) -> None:
        self.acquired_resources.append(
            AcquiredResource(
                resource=response.resource, release_key=response.release_key
            )
        )

    @asynccontextmanager
    async def acquire_resource(
        self,
        *,
        reattach: Optional[DetachedResource] = None,
        max_wait_time: timedelta = timedelta(minutes=5),
    ) -> AsyncGenerator[AcquiredResource, None]:
        warn_when_workflow_has_timeouts()
        self.lazy_register_signal_handler()

        if reattach is None:
            await self.send_acquire_signal()
            await workflow.wait_condition(
                lambda: len(self.acquired_resources) > 0, timeout=max_wait_time
            )
            resource = self.acquired_resources.pop(0)
        else:
            resource = AcquiredResource(
                resource=reattach.resource, release_key=reattach.release_key
            )

        # Can't happen, but the typechecker doesn't know about workflow.wait_condition
        if resource is None:
            raise RuntimeError("resource was None when it can't be")

        # During the yield, the calling workflow owns the resource. Note that this is a lock, not a lease! Our
        # finally block will release the resource if an activity fails. This is why we asserted the lack of
        # workflow-level timeouts above - the finally block wouldn't run if there was a timeout.
        try:
            yield resource
        finally:
            if not resource.detached:
                await self.send_release_signal(resource)


def warn_when_workflow_has_timeouts() -> None:
    if has_timeout(workflow.info().run_timeout):
        workflow.logger.warning(
            f"ResourceLockingWorkflow cannot have a run_timeout (found {workflow.info().run_timeout}) - this will leak locks"
        )
    if has_timeout(workflow.info().execution_timeout):
        workflow.logger.warning(
            f"ResourceLockingWorkflow cannot have an execution_timeout (found {workflow.info().execution_timeout}) - this will leak locks"
        )


def has_timeout(timeout: Optional[timedelta]) -> bool:
    # After continue_as_new, timeouts are 0, even if they were None before continue_as_new (and were not set in the
    # continue_as_new call).
    return timeout is not None and timeout > timedelta(0)
