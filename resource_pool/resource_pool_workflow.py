from dataclasses import dataclass
from datetime import timedelta
from typing import Optional

from temporalio import workflow

from resource_pool.shared import AcquireRequest, AcquireResponse


# Internal to this workflow, we'll associate randomly generated release signal names with each acquire request.
@dataclass
class InternalAcquireRequest(AcquireRequest):
    release_signal: Optional[str]


@dataclass
class ResourcePoolWorkflowInput:
    # Key is resource, value is current holder of the resource (None if not held)
    resources: dict[str, Optional[InternalAcquireRequest]]
    waiters: list[InternalAcquireRequest]


@workflow.defn
class ResourcePoolWorkflow:
    @workflow.init
    def __init__(self, input: ResourcePoolWorkflowInput) -> None:
        self.resources = input.resources
        self.waiters = input.waiters
        self.release_signal_to_resource: dict[str, str] = {}
        for resource, holder in self.resources.items():
            if holder is not None and holder.release_signal is not None:
                self.release_signal_to_resource[holder.release_signal] = resource

    @workflow.signal
    async def add_resources(self, resources: list[str]) -> None:
        for resource in resources:
            if resource in self.resources:
                workflow.logger.warning(
                    f"Ignoring attempt to add already-existing resource: {resource}"
                )
                continue

            self.resources[resource] = None
            if len(self.waiters) > 0:
                next_holder = self.waiters.pop(0)
                await self.assign_resource(resource, next_holder)

    @workflow.signal
    async def acquire_resource(self, request: AcquireRequest) -> None:
        internal_request = InternalAcquireRequest(
            workflow_id=request.workflow_id, release_signal=None
        )

        for resource, holder in self.resources.items():
            # Naively give out the first free resource, if we have one
            if holder is None:
                await self.assign_resource(resource, internal_request)
                return

        # Otherwise queue the request
        self.waiters.append(internal_request)
        workflow.logger.info(
            f"workflow_id={request.workflow_id} is waiting for a resource"
        )

    async def assign_resource(
        self, resource: str, internal_request: InternalAcquireRequest
    ) -> None:
        self.resources[resource] = internal_request
        workflow.logger.info(
            f"workflow_id={internal_request.workflow_id} acquired resource {resource}"
        )
        internal_request.release_signal = str(workflow.uuid4())
        self.release_signal_to_resource[internal_request.release_signal] = resource

        requester = workflow.get_external_workflow_handle(internal_request.workflow_id)
        await requester.signal(
            "assign_resource",
            AcquireResponse(
                release_signal_name=internal_request.release_signal, resource=resource
            ),
        )

    @workflow.signal(dynamic=True)
    async def release_resource(self, signal_name, *args) -> None:
        if not signal_name in self.release_signal_to_resource:
            workflow.logger.warning(
                f"Ignoring unknown signal: {signal_name} was not a valid release signal."
            )
            return

        resource = self.release_signal_to_resource[signal_name]

        holder = self.resources[resource]
        if holder is None:
            workflow.logger.warning(
                f"Ignoring request to release resource that is not held: {resource}"
            )
            return

        # Remove the current holder
        workflow.logger.info(
            f"workflow_id={holder.workflow_id} released resource {resource}"
        )
        self.resources[resource] = None
        del self.release_signal_to_resource[signal_name]

        # If there are queued requests, assign the resource to the next one
        if len(self.waiters) > 0:
            next_holder = self.waiters.pop(0)
            await self.assign_resource(resource, next_holder)

    @workflow.query
    def get_current_holders(self) -> dict[str, Optional[InternalAcquireRequest]]:
        return {k: v if v else None for k, v in self.resources.items()}

    @workflow.run
    async def run(self, _: ResourcePoolWorkflowInput) -> None:
        # Continue as new either when temporal tells us to, or every 12 hours (so it occurs semi-frequently)
        await workflow.wait_condition(
            lambda: workflow.info().is_continue_as_new_suggested(),
            timeout=timedelta(hours=12),
        )

        workflow.continue_as_new(
            ResourcePoolWorkflowInput(
                resources=self.resources,
                waiters=self.waiters,
            )
        )
