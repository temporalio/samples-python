from dataclasses import dataclass
from typing import Optional

from temporalio import workflow
from temporalio.exceptions import ApplicationError

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
        self.release_key_to_resource: dict[str, str] = {}

        for resource, holder in self.resources.items():
            if holder is not None and holder.release_signal is not None:
                self.release_key_to_resource[holder.release_signal] = resource

    @workflow.signal
    async def add_resources(self, resources: list[str]) -> None:
        for resource in resources:
            if resource in self.resources:
                workflow.logger.warning(
                    f"Ignoring attempt to add already-existing resource: {resource}"
                )
            else:
                self.resources[resource] = None

    @workflow.signal
    async def acquire_resource(self, request: AcquireRequest) -> None:
        self.waiters.append(
            InternalAcquireRequest(workflow_id=request.workflow_id, release_signal=None)
        )
        workflow.logger.info(
            f"workflow_id={request.workflow_id} is waiting for a resource"
        )

    @workflow.signal
    async def release_resource(self, acquire_response: AcquireResponse) -> None:
        release_key = acquire_response.release_key
        resource = self.release_key_to_resource.get(release_key)
        if resource is None:
            workflow.logger.warning(f"Ignoring unknown release_key: {release_key}")
            return

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
        del self.release_key_to_resource[release_key]

    @workflow.query
    def get_current_holders(self) -> dict[str, Optional[InternalAcquireRequest]]:
        return self.resources

    async def assign_resource(
        self, resource: str, internal_request: InternalAcquireRequest
    ) -> None:
        workflow.logger.info(
            f"workflow_id={internal_request.workflow_id} acquired resource {resource}"
        )

        requester = workflow.get_external_workflow_handle(internal_request.workflow_id)
        try:
            release_signal = str(workflow.uuid4())
            await requester.signal(
                f"assign_resource_{workflow.info().workflow_id}",
                AcquireResponse(release_key=release_signal, resource=resource),
            )

            internal_request.release_signal = release_signal
            self.resources[resource] = internal_request
            self.release_key_to_resource[release_signal] = resource
        except ApplicationError as e:
            if e.type == "ExternalWorkflowExecutionNotFound":
                workflow.logger.info(
                    f"Could not assign resource {resource} to {internal_request.workflow_id}: {e.message}"
                )
            else:
                raise e

    async def assign_next_resource(self) -> bool:
        if len(self.waiters) == 0:
            return False

        next_free_resource = self.get_free_resource()
        if next_free_resource is None:
            return False

        next_waiter = self.waiters.pop(0)
        await self.assign_resource(next_free_resource, next_waiter)
        return True

    def get_free_resource(self) -> Optional[str]:
        return next(
            (resource for resource, holder in self.resources.items() if holder is None),
            None,
        )

    def can_assign_resource(self) -> bool:
        return len(self.waiters) > 0 and self.get_free_resource() is not None

    def should_continue_as_new(self) -> bool:
        return (
            workflow.info().is_continue_as_new_suggested()
            and workflow.all_handlers_finished()
        )

    @workflow.run
    async def run(self, _: ResourcePoolWorkflowInput) -> None:
        while True:
            await workflow.wait_condition(
                lambda: self.can_assign_resource() or self.should_continue_as_new()
            )

            if await self.assign_next_resource():
                continue

            if self.should_continue_as_new():
                workflow.continue_as_new(
                    ResourcePoolWorkflowInput(
                        resources=self.resources,
                        waiters=self.waiters,
                    )
                )
