from dataclasses import dataclass
from temporalio.client import Client
from temporalio import activity, workflow
import asyncio
from temporalio.exceptions import ApplicationError

LOCK_ACQUIRED_SIGNAL_NAME = "acquire-lock-event"


@dataclass
class SignalWithStartMutexWorkflowInput:
    namespace: str
    resource_id: str
    unlock_timeout_seconds: float
    sender_workflow_id: str


@dataclass
class SignalWithStartMutexWorkflowResult:
    workflow_id: str


@dataclass
class MutexWorkflowInput:
    namespace: str
    resource_id: str
    unlock_timeout_seconds: float


@activity.defn
async def signal_with_start_mutex_workflow(
    params: SignalWithStartMutexWorkflowInput,
) -> SignalWithStartMutexWorkflowResult:
    # Create client connected to server at the given address
    client = await Client.connect("localhost:7233")

    workflow_id = f"mutex:{params.namespace}:{params.resource_id}"

    # Sends a signal to the workflow (and starts it if needed)
    wf_input = MutexWorkflowInput(
        namespace=params.namespace,
        resource_id=params.resource_id,
        unlock_timeout_seconds=params.unlock_timeout_seconds,
    )
    await client.start_workflow(
        workflow=MutexWorkflow.run,
        arg=wf_input,
        id=workflow_id,
        task_queue="mutex-task-queue",
        start_signal="request_lock",
        start_signal_args=[params.sender_workflow_id],
    )
    return SignalWithStartMutexWorkflowResult(workflow_id=workflow_id)


def generate_unlock_token(sender_workflow_id: str) -> str:
    return f"unlock-event-{sender_workflow_id}"


@workflow.defn
class MutexWorkflow:
    def __init__(self):
        self._lock_requests: asyncio.Queue[str] = asyncio.Queue()
        self._lock_releases: asyncio.Queue[str] = asyncio.Queue()

    @workflow.run
    async def run(self, params: MutexWorkflowInput) -> str:
        workflow.logger.info(f"Starting mutex workflow {workflow.info().workflow_id}")
        while True:
            # read lock signal
            if self._lock_requests.empty():
                break
            sender_workflow_id = self._lock_requests.get_nowait()

            # send release info to origin
            # TODO manage case when origin is closed
            unlock_token = generate_unlock_token(sender_workflow_id)
            handle = workflow.get_external_workflow_handle(sender_workflow_id)
            try:
                await handle.signal(LOCK_ACQUIRED_SIGNAL_NAME, unlock_token)
            except ApplicationError as e:
                if e.type == "ExternalWorkflowExecutionNotFound":
                    workflow.logger.warning(
                        f"Could not signal lock acquisition to caller {sender_workflow_id}: {e.message}"
                    )
                    continue
                else:
                    raise e

            # wait for release signal or timeout
            try:
                await workflow.wait_condition(
                    lambda: not self._lock_releases.empty(),
                    timeout=params.unlock_timeout_seconds,
                )
                # pop the release
                # TODO check it’s the right one
                if not self._lock_releases.empty():
                    self._lock_releases.get_nowait()

            # If timeout was reached, we release the lock
            except asyncio.TimeoutError:
                workflow.logger.warning(
                    f"Workflow {sender_workflow_id} did not release the lock before timeout was reached."
                )
                continue
        workflow.logger.info(f"Stopping mutex workflow {workflow.info().workflow_id}")

    @workflow.signal
    async def request_lock(self, sender_workflow_id: str):
        workflow.logger.info(f"Received lock request from {sender_workflow_id}")
        await self._lock_requests.put(sender_workflow_id)

    @workflow.signal
    async def release_lock(self, unlock_token: str):
        workflow.logger.info(f"Received lock release with token {unlock_token}")
        await self._lock_releases.put(unlock_token)
