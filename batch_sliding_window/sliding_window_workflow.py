import asyncio
from dataclasses import dataclass
from typing import Dict, List, Optional, Set

from temporalio import workflow
from temporalio.common import WorkflowIDReusePolicy

from batch_sliding_window.record_loader_activity import (
    RecordLoader,
    GetRecordsInput,
    SingleRecord,
)
from batch_sliding_window.record_processor_workflow import RecordProcessorWorkflow


@dataclass
class SlidingWindowWorkflowInput:
    """Contains SlidingWindowWorkflow arguments."""

    page_size: int
    sliding_window_size: int
    offset: int  # inclusive
    maximum_offset: int  # exclusive
    progress: int = 0
    # The set of record ids currently being processed
    current_records: Optional[Set[int]] = None


@dataclass
class SlidingWindowState:
    """Used as a 'state' query result."""

    current_records: List[int]  # record ids currently being processed
    children_started_by_this_run: int
    offset: int
    progress: int


@workflow.defn
class SlidingWindowWorkflow:
    """Workflow processes a range of records using a requested number of child workflows.

    As soon as a child workflow completes a new one is started.
    """

    def __init__(self):
        self.current_records: Set[int] = set()
        self.children_started_by_this_run = []
        self.offset = 0
        self.progress = 0
        self._completion_signals_received = 0

    @workflow.run
    async def run(self, input: SlidingWindowWorkflowInput) -> int:
        workflow.logger.info(
            f"SlidingWindowWorkflow started",
            extra={
                "sliding_window_size": input.sliding_window_size,
                "page_size": input.page_size,
                "offset": input.offset,
                "maximum_offset": input.maximum_offset,
                "progress": input.progress,
            },
        )

        # Initialize state from input
        self.current_records = input.current_records or set()
        self.offset = input.offset
        self.progress = input.progress

        # Set up query handler
        workflow.set_query_handler("state", self._handle_state_query)

        # Set up signal handler for completion notifications
        workflow.set_signal_handler("report_completion", self._handle_completion_signal)

        return await self._execute(input)

    async def _execute(self, input: SlidingWindowWorkflowInput) -> int:
        """Main execution logic."""
        # Get records for this page if we haven't reached the end
        records = []
        if self.offset < input.maximum_offset:
            get_records_input = GetRecordsInput(
                page_size=input.page_size,
                offset=self.offset,
                max_offset=input.maximum_offset,
            )
            get_records_output = await workflow.execute_activity(
                RecordLoader.get_records,
                get_records_input,
                start_to_close_timeout=workflow.timedelta(seconds=5),
            )
            records = get_records_output.records

        workflow_id = workflow.info().workflow_id

        # Process records
        for record in records:
            # Wait until we have capacity in the sliding window
            await workflow.wait_condition(
                lambda: len(self.current_records) < input.sliding_window_size
            )

            # Start child workflow for this record
            child_id = f"{workflow_id}/{record.id}"
            child_handle = await workflow.start_child_workflow(
                RecordProcessorWorkflow.run,
                record,
                id=child_id,
                id_reuse_policy=WorkflowIDReusePolicy.ALLOW_DUPLICATE,
                parent_close_policy=workflow.ParentClosePolicy.ABANDON,
            )

            self.children_started_by_this_run.append(child_handle)
            self.current_records.add(record.id)

        return await self._continue_as_new_or_complete(input)

    async def _continue_as_new_or_complete(
        self, input: SlidingWindowWorkflowInput
    ) -> int:
        """Continue-as-new after starting page_size children or complete if done."""
        # Update offset based on children started in this run
        new_offset = input.offset + len(self.children_started_by_this_run)

        if new_offset < input.maximum_offset:
            # In Python, await start_child_workflow() already waits until
            # the start has been accepted by the server, so no additional wait needed

            # Continue-as-new with updated state
            new_input = SlidingWindowWorkflowInput(
                page_size=input.page_size,
                sliding_window_size=input.sliding_window_size,
                offset=new_offset,
                maximum_offset=input.maximum_offset,
                progress=self.progress,
                current_records=self.current_records,
            )

            workflow.continue_as_new(new_input)

        # Last run in the continue-as-new chain
        # Wait for all children to complete
        await workflow.wait_condition(lambda: len(self.current_records) == 0)
        return self.progress

    def _handle_completion_signal(self, record_id: int) -> None:
        """Handle completion signal from child workflow."""
        # Check for duplicate signals
        if record_id in self.current_records:
            self.current_records.remove(record_id)
            self.progress += 1

    def _handle_state_query(self) -> SlidingWindowState:
        """Handle state query for monitoring."""
        current_record_ids = sorted(list(self.current_records))
        return SlidingWindowState(
            current_records=current_record_ids,
            children_started_by_this_run=len(self.children_started_by_this_run),
            offset=self.offset,
            progress=self.progress,
        )
