from contextlib import asynccontextmanager
from datetime import timedelta
from typing import Optional, AsyncGenerator

from temporalio.client import Client
from temporalio import workflow, activity
from temporalio.common import WorkflowIDConflictPolicy

from resource_locking.lock_manager_workflow import LockManagerWorkflowInput, LockManagerWorkflow
from resource_locking.shared import AcquireResponse, LOCK_MANAGER_WORKFLOW_ID, AcquireRequest, AcquiredResource

# Use this class in workflow code that that needs to run on locked resources.
class ResourceAllocator:
    def __init__(self, client: Client):
        self.client = client

    @activity.defn
    async def send_acquire_signal(self):
        info = activity.info()

        # This will start and signal the workflow if it isn't running, otherwise it will signal the current run.
        await self.client.start_workflow(
            workflow=LockManagerWorkflow.run,
            arg=LockManagerWorkflowInput(
                resources={},
                waiters=[],
            ),
            id=LOCK_MANAGER_WORKFLOW_ID,
            task_queue="default",
            id_conflict_policy=WorkflowIDConflictPolicy.USE_EXISTING,
            start_signal="acquire_resource",
            start_signal_args=[AcquireRequest(info.workflow_id)]
        )

    @classmethod
    @asynccontextmanager
    async def acquire_resource(cls, *, already_acquired_resource: Optional[AcquiredResource] = None, max_wait_time: timedelta = timedelta(minutes=5)):
        warn_when_workflow_has_timeouts()

        resource = already_acquired_resource
        if resource is None:
            async def assign_resource(input: AcquireResponse):
                workflow.set_signal_handler("assign_resource", None)
                nonlocal resource
                resource = AcquiredResource(
                    resource=input.resource,
                    release_signal_name=input.release_signal_name,
                )

            workflow.set_signal_handler("assign_resource", assign_resource)

            await workflow.execute_activity(
                ResourceAllocator.send_acquire_signal,
                start_to_close_timeout=timedelta(seconds=10),
            )

            await workflow.wait_condition(lambda: resource is not None, timeout=max_wait_time)

        # During the yield, the calling workflow owns the resource. Note that this is a lock, not a lease! Our
        # finally block will release the resource if an activity fails. This is why we asserted the lack of
        # workflow-level timeouts above - the finally block wouldn't run if there was a timeout.
        try:
            resource.autorelease = True
            yield resource
        finally:
            if resource.autorelease:
                handle = workflow.get_external_workflow_handle(LOCK_MANAGER_WORKFLOW_ID)
                await handle.signal(resource.release_signal_name)

def warn_when_workflow_has_timeouts():
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
