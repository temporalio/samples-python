from dataclasses import dataclass
from datetime import timedelta

from temporalio import workflow


@dataclass
class AssignedResource:
    resource: str


@dataclass
class AcquireRequest:
    workflow_id: str
    run_id: str


@dataclass
class ReleaseRequest:
    resource: str
    workflow_id: str
    run_id: str


@dataclass
class HandoffRequest:
    resource: str
    workflow_id: str
    old_run_id: str
    new_run_id: str


LOCK_MANAGER_WORKFLOW_ID = "lock_manager"


@dataclass
class LockManagerWorkflowInput:
    # Key is resource, value is users of the resource. The first item in each list is the current holder of the lease
    # on that resource. A similar data structure could allow for multiple holders (perhaps the first n items are the
    # current holders).
    resource_queues: dict[str, list[AcquireRequest]]


@workflow.defn
class LockManagerWorkflow:
    def __init__(self):
        self.resource_queues: dict[str, list[AcquireRequest]] = {}

    @workflow.signal
    async def acquire_resource(self, request: AcquireRequest):
        # A real-world version of this workflow probably wants to use more sophisticated load balancing strategies than
        # "first free" and "wait for a random one".

        for resource in self.resource_queues:
            # Naively give out the first free resource, if we have one
            if len(self.resource_queues[resource]) == 0:
                workflow.logger.info(
                    f"workflow_id={request.workflow_id} run_id={request.run_id} acquired resource {resource}"
                )
                self.resource_queues[resource].append(request)
                requester = workflow.get_external_workflow_handle(
                    request.workflow_id, run_id=request.run_id
                )
                await requester.signal("assign_resource", AssignedResource(resource))
                return

        # Otherwise put this resource in a random queue.
        resource = workflow.random().choice(list(self.resource_queues.keys()))
        workflow.logger.info(
            f"workflow_id={request.workflow_id} run_id={request.run_id} is waiting for resource {resource}"
        )
        self.resource_queues[resource].append(request)

    @workflow.signal
    async def release_resource(self, request: ReleaseRequest):
        queue = self.resource_queues[request.resource]
        if queue is None:
            workflow.logger.warning(
                f"Ignoring request from {request.workflow_id} to release non-existent resource: {request.resource}"
            )
            return

        if len(queue) == 0:
            workflow.logger.warning(
                f"Ignoring request from {request.workflow_id} to release resource that is not held: {request.resource}"
            )
            return

        holder = queue[0]
        if not (
            holder.workflow_id == request.workflow_id
            and holder.run_id == request.run_id
        ):
            workflow.logger.warning(
                f"Ignoring request from non-holder to release resource {request.resource}"
            )
            workflow.logger.warning(
                f"resource is currently held by wf_id={holder.workflow_id} run_id={holder.run_id}"
            )
            workflow.logger.warning(
                f"request was from wf_id={request.workflow_id} run_id={request.run_id}"
            )
            return

        # Remove the current holder from the head of the queue
        workflow.logger.info(
            f"workflow_id={request.workflow_id} run_id={request.run_id} released resource {request.resource}"
        )
        queue = queue[1:]
        self.resource_queues[request.resource] = queue

        # If there are queued requests, assign the resource to the next one
        if len(queue) > 0:
            next_holder = queue[0]
            workflow.logger.info(
                f"workflow_id={next_holder.workflow_id} run_id={next_holder.run_id} acquired resource {request.resource} after waiting"
            )
            requester = workflow.get_external_workflow_handle(
                next_holder.workflow_id, run_id=next_holder.run_id
            )
            await requester.signal(
                "assign_resource", AssignedResource(request.resource)
            )

    @workflow.signal
    async def handoff_resource(self, request: HandoffRequest):
        queue = self.resource_queues[request.resource]
        if queue is None:
            workflow.logger.warning(
                f"Ignoring request from {request.workflow_id} to hand off non-existent resource: {request.resource}"
            )
            return

        if len(queue) == 0:
            workflow.logger.warning(
                f"Ignoring request from {request.workflow_id} to hand off resource that is not held: {request.resource}"
            )
            return

        holder = queue[0]
        if not (
            holder.workflow_id == request.workflow_id
            and holder.run_id == request.old_run_id
        ):
            workflow.logger.warning(
                f"Ignoring request from non-holder to hand off resource {request.resource}"
            )
            workflow.logger.warning(
                f"resource is currently held by wf_id={holder.workflow_id} run_id={holder.run_id}"
            )
            workflow.logger.warning(
                f"request was from wf_id={request.workflow_id} run_id={request.old_run_id}"
            )
            return

        workflow.logger.info(
            f"workflow_id={request.workflow_id} handed off resource {request.resource} from run_id={request.old_run_id} to run_id={request.new_run_id}"
        )
        queue[0] = AcquireRequest(request.workflow_id, request.new_run_id)
        requester = workflow.get_external_workflow_handle(
            request.workflow_id, run_id=request.new_run_id
        )
        await requester.signal("assign_resource", AssignedResource(request.resource))

    @workflow.query
    def get_current_holders(self) -> dict[str, AcquireRequest]:
        return {k: v[0] if v else None for k, v in self.resource_queues.items()}

    @workflow.run
    async def run(self, input: LockManagerWorkflowInput) -> None:
        self.resource_queues = input.resource_queues

        # Continue as new either when temporal tells us to, or every 12 hours (so it occurs semi-frequently)
        await workflow.wait_condition(
            lambda: workflow.info().is_continue_as_new_suggested(),
            timeout=timedelta(hours=12),
        )

        workflow.continue_as_new(LockManagerWorkflowInput(self.resource_queues))
