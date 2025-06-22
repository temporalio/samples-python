from typing import Callable
from datetime import timedelta
from temporalio import workflow

from mutexworkflow import (
    SignalWithStartMutexWorkflowInput,
    MutexWorkflow,
    signal_with_start_mutex_workflow,
    LOCK_ACQUIRED_SIGNAL_NAME,
)


@workflow.defn
class SampleWorkflowWithMutex:
    def __init__(self):
        self.unlock_token: str | None = None

    @workflow.run
    async def run(self, resource_id: str) -> str:
        workflow.logger.info(f"Starting workflow")
        # acquire lock
        unlock_func = await self.lock(resource_id, timedelta(minutes=2.0))
        # do critical work (mutex section)
        workflow.logger.info("Doing critical work.")
        await workflow.sleep(2.0)
        # release lock
        await unlock_func()
        workflow.logger.info(f"Stopping workflow")
        return workflow.info().workflow_id

    async def lock(
        self, resource_id: str, unlock_timeout: timedelta
    ) -> Callable[[], None]:
        """lock resource"""
        # request a lock
        params = SignalWithStartMutexWorkflowInput(
            namespace=workflow.info().namespace,
            sender_workflow_id=workflow.info().workflow_id,
            resource_id=resource_id,
            unlock_timeout_seconds=unlock_timeout.total_seconds(),
        )
        result = await workflow.execute_local_activity(
            signal_with_start_mutex_workflow,
            params,
            start_to_close_timeout=timedelta(seconds=5.0),
        )
        # wait to acquire lock from mutex workflow
        await workflow.wait_condition(lambda: self.unlock_token is not None)
        unlock_token = self.unlock_token

        # return function to unlock
        async def unlock_function():
            wf_handle = workflow.get_external_workflow_handle(
                workflow_id=result.workflow_id
            )
            await wf_handle.signal(MutexWorkflow.release_lock, unlock_token)

        return unlock_function

    @workflow.signal(name=LOCK_ACQUIRED_SIGNAL_NAME)
    def acquired_lock(self, unlock_token: str):
        self.unlock_token = unlock_token
