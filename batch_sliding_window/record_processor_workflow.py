import asyncio
import random

from temporalio import workflow

from batch_sliding_window.record_loader_activity import SingleRecord


@workflow.defn
class RecordProcessorWorkflow:
    """Workflow that implements processing of a single record."""

    @workflow.run
    async def run(self, record: SingleRecord) -> None:
        await self._process_record(record)
        
        # Notify parent about completion via signal
        parent = workflow.info().parent
        
        # This workflow is always expected to have a parent.
        # But for unit testing it might be useful to skip the notification if there is none.
        if parent:
            # Don't specify run_id as parent calls continue-as-new
            await workflow.external_workflow_handle(parent.workflow_id).signal(
                "report_completion", record.id
            )

    async def _process_record(self, record: SingleRecord) -> None:
        """Simulate application specific record processing."""
        # Use workflow.random() to get a random number to ensure workflow determinism
        sleep_duration = workflow.random().randint(1, 10)
        await workflow.sleep(sleep_duration)
        
        workflow.logger.info(f"Processed record {record}") 