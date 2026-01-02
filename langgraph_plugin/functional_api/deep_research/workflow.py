"""Deep Research Agent Workflow.

Temporal workflow for the deep research agent.
"""

from typing import Any

from temporalio import workflow
from temporalio.contrib.langgraph import compile_functional


@workflow.defn
class DeepResearchWorkflow:
    """Temporal workflow for deep research.

    Demonstrates long-running research workflows with:
    - Parallel search execution
    - Iterative research refinement
    - Report synthesis

    Each task runs as a Temporal activity with automatic retries.
    """

    @workflow.run
    async def run(self, topic: str) -> dict[str, Any]:
        """Run deep research on a topic.

        Args:
            topic: The research topic.

        Returns:
            Research report with metadata.
        """
        app = compile_functional("deep_research_entrypoint")
        result = await app.ainvoke(topic)
        return result
