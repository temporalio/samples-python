"""Reflection Agent Workflow.

Temporal workflow that executes the reflection agent with durable execution.
"""

from typing import Any

from temporalio import workflow
from temporalio.contrib.langgraph import compile


@workflow.defn
class ReflectionWorkflow:
    """Temporal workflow that executes a reflection agent.

    The reflection pattern iteratively improves content by:
    1. Generating initial content
    2. Critiquing and scoring
    3. Revising based on feedback
    4. Repeating until quality threshold

    Each @task runs as a Temporal activity, so LLM calls are
    automatically retried on failure and the workflow survives
    worker crashes.
    """

    @workflow.run
    async def run(
        self, task_description: str, max_iterations: int = 3
    ) -> dict[str, Any]:
        """Run the reflection agent.

        Args:
            task_description: The writing/generation task.
            max_iterations: Maximum reflection iterations.

        Returns:
            The final content with iteration history.
        """
        app = compile("reflection_entrypoint")

        # Pass max_iterations through config or as part of input
        result = await app.ainvoke(task_description)

        return result
