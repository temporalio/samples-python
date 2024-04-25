from datetime import datetime, timedelta

from dataclasses import dataclass

from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import ActivityError

with workflow.unsafe.imports_passed_through():
    from batch.activities import (
        ListRecordActivityInput,
        list_records,
        ProcessRecordActivityInput,
        process_record,
    )


@dataclass
class RecordProcessorWorkflowInput:
    day: str
    record_uri: str


@workflow.defn
class RecordProcessor:
    @workflow.run
    async def run(self, workflow_input: RecordProcessorWorkflowInput) -> str:
        list_records_input = ListRecordActivityInput(
            record_filter="taste=yummy", day=workflow_input.day
        )

        record_uri_list = await workflow.execute_activity(
            list_records,
            list_records_input,
            start_to_close_timeout=timedelta(minutes=5),
        )
        try:
            for key in record_uri_list:
                process_record_input = ProcessRecordActivityInput(uri=key)
                await workflow.execute_activity(
                    process_record,
                    process_record_input,
                    start_to_close_timeout=timedelta(minutes=1),
                )

        except ActivityError as output_err:
            workflow.logger.error(f"failed: {output_err}")
            raise output_err


@dataclass
class DailyBatchWorkflowInput:
    start_day: str
    end_day: str
    record_filter: str


@workflow.defn
class DailyBatch:
    """DailyBatch workflow"""

    @workflow.run
    async def run(self, workflow_input: DailyBatchWorkflowInput) -> str:
        if workflow_input.start_day == workflow_input.end_day:
            return ""

        await workflow.execute_child_workflow(
            RecordProcessor.run,
            RecordProcessorWorkflowInput(
                day=workflow_input.start_day, record_uri=workflow_input.record_filter
            ),
        )

        next_start_day = (
            datetime.strptime(workflow_input.start_day, "%Y-%m-%d") + timedelta(days=1)
        ).strftime("%Y-%m-%d")

        return workflow.continue_as_new(
            DailyBatchWorkflowInput(
                start_day=next_start_day,
                end_day=workflow_input.end_day,
                record_filter=workflow_input.record_filter,
            )
        )
