"""On-complete operation that receives the outcome of a standalone Nexus operation."""

from dataclasses import dataclass

import nexusrpc.handler
from temporalio import nexus
from temporalio.common import WorkflowIDConflictPolicy
from temporalio.nexus import notifications

from nexus_completion_callbacks.caller.workflows import (
    RecordCompletionInput,
    RecordCompletionWorkflow,
)
from nexus_completion_callbacks.service import GreetingOutput


@dataclass
class CallbackContext:
    """Source context the caller attaches to the completion callback."""

    operation_id: str


@nexusrpc.handler.service_handler(name="GreetingCompletionService")
class GreetingCompletionHandler:
    @nexus.temporal_operation
    async def on_complete(
        self,
        _ctx: nexus.TemporalStartOperationContext,
        client: nexus.TemporalNexusClient,
        input: notifications.OnCompleteRequest[GreetingOutput, CallbackContext],
    ) -> nexus.TemporalOperationResult[notifications.OnCompleteResponse]:
        operation_id = input.source_context.operation_id
        if isinstance(input.result, notifications.OnCompleteRequestResultSuccess):
            record = RecordCompletionInput(
                operation_id, message=input.result.value.message
            )
        else:
            record = RecordCompletionInput(operation_id, error=str(input.result.value))
        # Hand the outcome to a workflow so it's processed durably.
        # USE_EXISTING reuses the running workflow if the callback is redelivered.
        return await client.start_workflow(
            RecordCompletionWorkflow.run,
            record,
            id=f"on-complete-{operation_id}",
            id_conflict_policy=WorkflowIDConflictPolicy.USE_EXISTING,
        )
