"""Deep Research Agent Workflow.

Temporal workflow that executes the deep research agent with durable execution.

Note: This module only contains the workflow definition. The graph definition
is in graph.py and is only imported by the worker (not by this workflow module).
This separation is required because LangGraph cannot be imported in the
workflow sandbox.
"""

from typing import Any

from temporalio import workflow
from temporalio.contrib.langgraph import compile


@workflow.defn
class DeepResearchWorkflow:
    """Temporal workflow that executes deep research with durable execution.

    This workflow performs multi-step research on a topic:
    1. Plans research queries
    2. Executes parallel searches
    3. Evaluates and iterates if needed
    4. Synthesizes a comprehensive report

    The Temporal integration ensures:
    - Each search runs as a separate activity (parallel execution)
    - Research survives worker crashes
    - Long-running research (minutes to hours) completes reliably
    - Progress is visible through workflow history
    """

    @workflow.run
    async def run(
        self, topic: str, max_iterations: int = 2
    ) -> dict[str, Any]:
        """Run deep research on a topic.

        Args:
            topic: The research topic or question.
            max_iterations: Maximum research iterations (default 2).

        Returns:
            The final state containing the research report.
        """
        app = compile("deep_research")

        result = await app.ainvoke(
            {
                "messages": [{"role": "user", "content": topic}],
                "search_results": [],
                "iteration": 0,
                "max_iterations": max_iterations,
            }
        )

        return result
