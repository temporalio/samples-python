from dataclasses import dataclass
from datetime import timedelta
from typing import Optional

from temporalio import workflow

from resource_locking.shared import (
    AcquireRequest,
    AcquireResponse,
)

# Internal to this workflow, we'll associate randomly generated release signal names with each acquire request.
@dataclass
class InternalAcquireRequest(AcquireRequest):
    release_signal: Optional[str]

@dataclass
class LockManagerWorkflowInput:
    # Key is resource, value is users of the resource. The first item in each list is the current holder of the lock
    # on that resource. A similar data structure could allow for multiple holders (perhaps the first n items are the
    # current holders).
    resource_queues: dict[str, list[InternalAcquireRequest]]

@workflow.defn
class LockManagerWorkflow:
    @workflow.init
    def __init__(self, input: LockManagerWorkflowInput):
        self.resource_queues = input.resource_queues
        self.release_signal_to_resource: dict[str, str] = {}
        for resource, queue in self.resource_queues.items():
            if len(queue) > 0:
                self.release_signal_to_resource[queue[0].release_signal] = resource

    @workflow.signal
    async def acquire_resource(self, request: AcquireRequest):
        internal_request = InternalAcquireRequest(workflow_id=request.workflow_id, release_signal=None)

        # A real-world version of this workflow probably wants to use more sophisticated load balancing strategies than
        # "first free" and "wait for a random one".

        for resource in self.resource_queues:
            # Naively give out the first free resource, if we have one
            if len(self.resource_queues[resource]) == 0:
                self.resource_queues[resource].append(internal_request)
                await self.notify_acquirer(resource)
                return

        # Otherwise put this request in a random queue.
        resource = workflow.random().choice(list(self.resource_queues.keys()))
        workflow.logger.info(
            f"workflow_id={request.workflow_id} is waiting for resource {resource}"
        )
        self.resource_queues[resource].append(internal_request)

    async def notify_acquirer(self, resource: str):
        acquirer = self.resource_queues[resource][0]
        workflow.logger.info(
            f"workflow_id={acquirer.workflow_id} acquired resource {resource}"
        )
        acquirer.release_signal = str(workflow.uuid4())
        self.release_signal_to_resource[acquirer.release_signal] = resource

        requester = workflow.get_external_workflow_handle(acquirer.workflow_id)
        await requester.signal("assign_resource", AcquireResponse(release_signal_name=acquirer.release_signal, resource=resource))

    @workflow.signal(dynamic=True)
    async def release_resource(self, signal_name, *args):
        if not signal_name in self.release_signal_to_resource:
            workflow.logger.warning(f"Ignoring unknown signal: {signal_name} was not a valid release signal.")
            return

        resource = self.release_signal_to_resource[signal_name]

        queue = self.resource_queues[resource]
        if queue is None:
            workflow.logger.warning(
                f"Ignoring request to release non-existent resource: {resource}"
            )
            return

        if len(queue) == 0:
            workflow.logger.warning(
                f"Ignoring request to release resource that is not locked: {resource}"
            )
            return

        holder = queue[0]

        # Remove the current holder from the head of the queue
        workflow.logger.info(
            f"workflow_id={holder.workflow_id} released resource {resource}"
        )
        queue = queue[1:]
        self.resource_queues[resource] = queue
        del self.release_signal_to_resource[signal_name]

        # If there are queued requests, assign the resource to the next one
        if len(queue) > 0:
            await self.notify_acquirer(resource)

    @workflow.query
    def get_current_holders(self) -> dict[str, Optional[InternalAcquireRequest]]:
        return {k: v[0] if v else None for k, v in self.resource_queues.items()}

    @workflow.run
    async def run(self, input: LockManagerWorkflowInput) -> None:
        # Continue as new either when temporal tells us to, or every 12 hours (so it occurs semi-frequently)
        await workflow.wait_condition(
            lambda: workflow.info().is_continue_as_new_suggested(),
            timeout=timedelta(hours=12),
        )

        workflow.continue_as_new(LockManagerWorkflowInput(self.resource_queues))
