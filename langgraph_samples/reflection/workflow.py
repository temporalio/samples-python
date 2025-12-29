"""Reflection Agent Workflow.

Temporal workflow that executes the reflection agent with durable execution.

Note: This module only contains the workflow definition. The graph definition
is in graph.py and is only imported by the worker (not by this workflow module).
This separation is required because LangGraph cannot be imported in the
workflow sandbox.
"""

from typing import Any

from temporalio import workflow
from temporalio.contrib.langgraph import compile


@workflow.defn
class ReflectionWorkflow:
    """Temporal workflow that executes a reflection agent.

    This workflow:
    1. Generates initial content
    2. Reflects and critiques the content
    3. Revises based on feedback
    4. Loops until quality criteria met or max iterations

    The Temporal integration ensures:
    - Each generation/reflection/revision runs as an activity
    - Progress is saved after each iteration
    - Long refinement sessions complete reliably
    - Quality improvement is visible in workflow history
    """

    @workflow.run
    async def run(
        self, task: str, max_iterations: int = 3
    ) -> dict[str, Any]:
        """Run the reflection agent on a writing task.

        Args:
            task: The content generation task.
            max_iterations: Maximum refinement iterations (default 3).

        Returns:
            The final state containing the refined content.
        """
        app = compile("reflection")

        result = await app.ainvoke(
            {
                "messages": [{"role": "user", "content": task}],
                "critiques": [],
                "iteration": 0,
                "max_iterations": max_iterations,
            }
        )

        return result
