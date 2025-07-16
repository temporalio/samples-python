from dataclasses import dataclass
from typing import List
import asyncio

from temporalio import workflow
from temporalio.common import WorkflowIDReusePolicy
from temporalio.exceptions import ApplicationError

from .record_loader_activity import RecordLoader
from .sliding_window_workflow import SlidingWindowWorkflow, SlidingWindowWorkflowInput


@dataclass
class ProcessBatchWorkflowInput:
    """Input for the ProcessBatchWorkflow.
    
    A single input structure is preferred to multiple workflow arguments 
    to simplify backward compatible API changes.
    """
    page_size: int  # Number of children started by a single sliding window workflow run
    sliding_window_size: int  # Maximum number of children to run in parallel
    partitions: int  # How many sliding windows to run in parallel


@workflow.defn
class ProcessBatchWorkflow:
    """Sample workflow that partitions the data set into continuous ranges.
    
    A real application can choose any other way to divide the records 
    into multiple collections.
    """

    @workflow.run
    async def run(self, input: ProcessBatchWorkflowInput) -> int:
        # Get total record count
        record_count = await workflow.execute_activity(
            RecordLoader.get_record_count,
            start_to_close_timeout=workflow.timedelta(seconds=5),
        )

        if input.sliding_window_size < input.partitions:
            raise ApplicationError(
                "SlidingWindowSize cannot be less than number of partitions"
            )

        partitions = self._divide_into_partitions(record_count, input.partitions)
        window_sizes = self._divide_into_partitions(input.sliding_window_size, input.partitions)

        workflow.logger.info(
            f"ProcessBatchWorkflow started",
            extra={
                "input": input,
                "record_count": record_count,
                "partitions": partitions,
                "window_sizes": window_sizes,
            }
        )

        # Start child workflows for each partition
        tasks = []
        offset = 0
        
        for i in range(input.partitions):
            # Make child id more user-friendly
            child_id = f"{workflow.info().workflow_id}/{i}"
            
            # Define partition boundaries
            maximum_partition_offset = offset + partitions[i]
            if maximum_partition_offset > record_count:
                maximum_partition_offset = record_count
            
            child_input = SlidingWindowWorkflowInput(
                page_size=input.page_size,
                sliding_window_size=window_sizes[i],
                offset=offset,  # inclusive
                maximum_offset=maximum_partition_offset,  # exclusive
                progress=0,
                current_records=None,
            )
            
            task = workflow.execute_child_workflow(
                SlidingWindowWorkflow.run,
                child_input,
                id=child_id,
                id_reuse_policy=WorkflowIDReusePolicy.ALLOW_DUPLICATE,
            )
            tasks.append(task)
            offset += partitions[i]

        # Wait for all child workflows to complete
        results = await asyncio.gather(*tasks)
        return sum(results)

    def _divide_into_partitions(self, number: int, n: int) -> List[int]:
        """Divide a number into n partitions as evenly as possible."""
        base = number // n
        remainder = number % n
        partitions = [base] * n

        for i in range(remainder):
            partitions[i] += 1

        return partitions 