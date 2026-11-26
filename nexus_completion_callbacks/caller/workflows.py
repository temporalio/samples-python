"""Workflow that records the outcome delivered by a completion callback."""

from dataclasses import dataclass

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from temporalio.nexus import notifications


@dataclass
class RecordCompletionInput:
    operation_id: str
    message: str | None = None
    error: str | None = None


@workflow.defn
class RecordCompletionWorkflow:
    """Durable record of a completion callback."""

    @workflow.run
    async def run(
        self, input: RecordCompletionInput
    ) -> notifications.OnCompleteResponse:
        if input.error is None:
            workflow.logger.info(
                "Operation %s succeeded: %s", input.operation_id, input.message
            )
        else:
            workflow.logger.info(
                "Operation %s failed: %s", input.operation_id, input.error
            )
        return notifications.OnCompleteResponse()
