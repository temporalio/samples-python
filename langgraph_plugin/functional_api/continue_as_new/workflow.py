"""Continue-as-New Workflow for LangGraph Functional API.

This workflow uses should_continue callback to stop execution after
a configurable number of tasks, then uses continue-as-new to resume from
where it left off. The entrypoint itself has NO knowledge of continue-as-new.
"""

from dataclasses import dataclass
from typing import Any, cast

from temporalio import workflow
from temporalio.contrib.langgraph import (
    CHECKPOINT_KEY,
    TemporalFunctionalRunner,
    compile,
)


@dataclass
class PipelineInput:
    """Input for the pipeline workflow."""

    value: int
    # Number of tasks to execute before continue-as-new
    tasks_per_execution: int = 3
    # Checkpoint from previous execution (None for first execution)
    checkpoint: dict[str, Any] | None = None


@workflow.defn
class ContinueAsNewWorkflow:
    """Workflow demonstrating continue-as-new with should_continue callback.

    The workflow uses should_continue callback to stop execution after
    a configurable number of tasks, then continues-as-new to resume.
    This demonstrates how to use continue-as-new with Functional API without
    the entrypoint needing any knowledge of Temporal.

    This demonstrates that:
    - Task results are cached in memory
    - should_continue callback controls when to checkpoint
    - get_state() serializes the cache for continue-as-new
    - compile(checkpoint=...) restores the cache in the new execution
    - Cached tasks return immediately without re-execution
    """

    @workflow.run
    async def run(self, input_data: PipelineInput) -> dict[str, Any]:
        """Execute the pipeline with continue-as-new checkpoint.

        Args:
            input_data: Pipeline input with value, tasks_per_execution, and checkpoint.

        Returns:
            Final result after all tasks complete.
        """
        # Track tasks executed in this execution
        tasks_executed = 0

        def should_continue() -> bool:
            """Stop after configured number of tasks."""
            nonlocal tasks_executed
            tasks_executed += 1
            return tasks_executed <= input_data.tasks_per_execution

        # Create runner, restoring from checkpoint if provided
        # Cast to TemporalFunctionalRunner since we know this is a Functional API entrypoint
        app = cast(
            TemporalFunctionalRunner,
            compile("pipeline_entrypoint", checkpoint=input_data.checkpoint),
        )

        # Execute the entrypoint with should_continue callback
        result = await app.ainvoke(
            {"value": input_data.value},
            should_continue=should_continue,
        )

        # Check if we stopped for checkpointing (more work to do)
        if CHECKPOINT_KEY in result:
            checkpoint = result[CHECKPOINT_KEY]

            workflow.logger.info(
                f"Stopping after {tasks_executed} tasks for checkpointing"
            )

            # Continue-as-new with checkpoint
            workflow.continue_as_new(
                PipelineInput(
                    value=input_data.value,
                    tasks_per_execution=input_data.tasks_per_execution,
                    checkpoint=checkpoint,
                )
            )

        # Entrypoint completed - return final result
        workflow.logger.info(f"Pipeline completed. Result: {result}")
        return result
