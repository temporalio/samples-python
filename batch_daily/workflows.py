import asyncio
from datetime import datetime, timedelta

from dataclasses import dataclass
import time
from typing import Any, Dict, Optional

from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import ActivityError
from temporalio.common import SearchAttributeKey

with workflow.unsafe.imports_passed_through():
    from batch_daily.activities import (
        ListRecordActivityInput,
        list_records,
        ProcessRecordActivityInput,
        process_record,
    )

TASK_QUEUE_NAME = "MY_TASK_QUEUE"


@dataclass
class RecordBatchProcessorWorkflowInput:
    record_filter: str
    day: Optional[str] = None


@workflow.defn
class RecordBatchProcessor:
    @workflow.run
    async def run(
        self, workflow_input: RecordBatchProcessorWorkflowInput
    ) -> Dict[str, Any]:
        if workflow_input.day is None:
            schedule_time = workflow.info().typed_search_attributes.get(
                SearchAttributeKey.for_datetime("TemporalScheduledStartTime")
            )
            assert schedule_time is not None, "when not scheduled, day must be provided"
            workflow_input.day = schedule_time.strftime("%Y-%m-%d")

        print(f"starting RecordProcessor with {workflow_input}")

        list_records_input = ListRecordActivityInput(
            record_filter=workflow_input.record_filter, day=workflow_input.day
        )

        record_uri_list = await workflow.execute_activity(
            list_records,
            list_records_input,
            start_to_close_timeout=timedelta(minutes=5),
        )

        task_list = []
        async with asyncio.TaskGroup() as tg:
            for key in record_uri_list:
                process_record_input = ProcessRecordActivityInput(uri=key)
                task_list.append(
                    tg.create_task(
                        workflow.execute_activity(
                            process_record,
                            process_record_input,
                            start_to_close_timeout=timedelta(minutes=1),
                        )
                    )
                )
        total_runtime = sum(map(lambda task: task.result()["runtime"], task_list))
        return {"runtime": total_runtime}


@dataclass
class DailyBatchWorkflowInput:
    start_day: str
    end_day: str
    record_filter: str


@workflow.defn
class DailyBatch:
    """DailyBatch workflow"""

    @workflow.run
    async def run(self, workflow_input: DailyBatchWorkflowInput) -> Dict[str, Any]:
        print(f"starting DailyBatch with {workflow_input}")

        start = datetime.strptime(workflow_input.start_day, "%Y-%m-%d")
        end = datetime.strptime(workflow_input.end_day, "%Y-%m-%d")
        task_list = []
        async with asyncio.TaskGroup() as tg:
            for day in [
                start + timedelta(days=x) for x in range(0, (end - start).days)
            ]:
                task_list.append(
                    tg.create_task(
                        workflow.execute_child_workflow(
                            RecordBatchProcessor.run,
                            RecordBatchProcessorWorkflowInput(
                                day=day.strftime("%Y-%m-%d"),
                                record_filter=workflow_input.record_filter,
                            ),
                        )
                    )
                )
        total_runtime = sum(map(lambda task: task.result()["runtime"], task_list))
        return {"runtime": total_runtime}
