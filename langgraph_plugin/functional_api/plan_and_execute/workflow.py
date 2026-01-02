"""Plan-and-Execute Agent Workflow.

Temporal workflow for the plan-and-execute agent.
"""

from typing import Any

from temporalio import workflow
from temporalio.contrib.langgraph import compile_functional


@workflow.defn
class PlanExecuteWorkflow:
    """Temporal workflow for plan-and-execute agent.

    The agent:
    1. Creates a plan with specific steps
    2. Executes each step using tools
    3. Generates a final response

    Each task runs as a Temporal activity with automatic retries.
    """

    @workflow.run
    async def run(self, objective: str) -> dict[str, Any]:
        """Run the plan-and-execute agent.

        Args:
            objective: The task to accomplish.

        Returns:
            Plan, step results, and final response.
        """
        app = compile_functional("plan_execute_entrypoint")
        result = await app.ainvoke(objective)
        return result
