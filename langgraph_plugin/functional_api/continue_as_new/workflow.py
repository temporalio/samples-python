"""Continue-as-New Workflow for LangGraph Functional API.

Demonstrates task result caching across continue-as-new boundaries.
"""

from dataclasses import dataclass
from typing import Any

from temporalio import workflow
from temporalio.contrib.langgraph import compile


@dataclass
class PipelineInput:
    """Input for the pipeline workflow."""

    value: int
    checkpoint: dict[str, Any] | None = None
    phase: int = 1  # 1 = first run (3 tasks), 2 = second run (all 5)


@workflow.defn
class ContinueAsNewWorkflow:
    """Workflow demonstrating continue-as-new with task caching.

    This workflow runs in two phases:
    1. Phase 1: Execute tasks 1-3, cache results, continue-as-new
    2. Phase 2: Execute all 5 tasks (1-3 use cached results, 4-5 execute fresh)

    This demonstrates that:
    - Task results are cached in memory
    - get_state() serializes the cache for continue-as-new
    - compile(checkpoint=...) restores the cache in the new execution
    - Cached tasks return immediately without re-execution
    """

    @workflow.run
    async def run(self, input_data: PipelineInput) -> dict[str, Any]:
        """Execute the pipeline with continue-as-new checkpoint.

        Args:
            input_data: Pipeline input with value, checkpoint, and phase.

        Returns:
            Final result after all 5 tasks complete.
        """
        # Compile with checkpoint to restore cached task results
        app = compile("pipeline_entrypoint", checkpoint=input_data.checkpoint)

        if input_data.phase == 1:
            # Phase 1: Run first 3 tasks only
            workflow.logger.info("Phase 1: Executing tasks 1-3")
            result = await app.ainvoke(
                {
                    "value": input_data.value,
                    "stop_after": 3,
                }
            )
            workflow.logger.info(f"Phase 1 result: {result}")

            # Get checkpoint with cached task results
            checkpoint: dict[str, Any] = app.get_state()  # type: ignore[assignment]

            # Continue-as-new with checkpoint for phase 2
            workflow.logger.info("Continuing as new for phase 2...")
            workflow.continue_as_new(
                PipelineInput(
                    value=input_data.value,
                    checkpoint=checkpoint,
                    phase=2,
                )
            )

        # Phase 2: Run all 5 tasks (tasks 1-3 are cached)
        workflow.logger.info("Phase 2: Executing all 5 tasks (1-3 cached)")
        result = await app.ainvoke(
            {
                "value": input_data.value,
                "stop_after": 5,
            }
        )
        workflow.logger.info(f"Final result: {result}")

        return result
