"""Plan-and-Execute Agent Workflow.

Temporal workflow that executes the plan-and-execute agent with durable execution.

Note: This module only contains the workflow definition. The graph definition
is in graph.py and is only imported by the worker (not by this workflow module).
This separation is required because LangGraph cannot be imported in the
workflow sandbox.
"""

from typing import Any

from temporalio import workflow
from temporalio.contrib.langgraph import compile


@workflow.defn
class PlanAndExecuteWorkflow:
    """Temporal workflow that executes a plan-and-execute agent.

    This workflow:
    1. Creates a plan from the objective
    2. Executes each step sequentially
    3. Replans if steps fail
    4. Returns the final result

    The Temporal integration ensures:
    - Each step runs as a separate activity
    - Failed steps can be retried or replanned
    - Progress is checkpointed after each step
    - Long-running plans complete reliably
    """

    @workflow.run
    async def run(self, objective: str) -> dict[str, Any]:
        """Run the plan-and-execute agent.

        Args:
            objective: The task to accomplish.

        Returns:
            The final state containing the execution results.
        """
        app = compile("plan_and_execute")

        result = await app.ainvoke(
            {
                "messages": [{"role": "user", "content": objective}],
                "step_results": [],
                "current_step": 0,
                "needs_replan": False,
            }
        )

        return result
