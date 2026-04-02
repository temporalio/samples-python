"""Supervisor Multi-Agent Workflow.

Temporal workflow that executes the supervisor multi-agent system.
"""

from typing import Any

from temporalio import workflow
from temporalio.contrib.langgraph import compile


@workflow.defn
class SupervisorWorkflow:
    """Temporal workflow that executes a supervisor multi-agent system.

    The supervisor coordinates three specialized agents:
    - Researcher: Gathers information
    - Writer: Creates content
    - Analyst: Performs calculations

    Each agent's work runs as a Temporal activity with automatic retries.
    """

    @workflow.run
    async def run(self, query: str) -> dict[str, Any]:
        """Run the supervisor multi-agent system.

        Args:
            query: The user's request.

        Returns:
            The final result with conversation history.
        """
        app = compile("supervisor_entrypoint")
        result = await app.ainvoke(query)
        return result
