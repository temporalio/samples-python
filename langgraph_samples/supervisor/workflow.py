"""Supervisor Multi-Agent Workflow.

Temporal workflow that executes the supervisor multi-agent system with durable execution.

Note: This module only contains the workflow definition. The graph definition
is in graph.py and is only imported by the worker (not by this workflow module).
This separation is required because LangGraph cannot be imported in the
workflow sandbox.
"""

from typing import Any

from temporalio import workflow
from temporalio.contrib.langgraph import compile


@workflow.defn
class SupervisorWorkflow:
    """Temporal workflow that executes a supervisor multi-agent system.

    This workflow uses a supervisor pattern where a central coordinator
    routes tasks to specialized agents (researcher, writer, analyst).
    Each agent's execution runs as Temporal activities:
    - The supervisor's routing decisions run as activities
    - Each specialized agent's work runs as activities
    - Agent handoffs are durably recorded

    If any agent fails, it is automatically retried. If the worker crashes,
    execution resumes from the last completed agent interaction.
    """

    @workflow.run
    async def run(self, request: str) -> dict[str, Any]:
        """Run the supervisor multi-agent system to handle a request.

        The supervisor will:
        1. Analyze the request to determine which agent(s) are needed
        2. Route tasks to appropriate specialized agents
        3. Coordinate agent interactions and handoffs
        4. Synthesize a final response from agent outputs

        Args:
            request: The user's request or task description.

        Returns:
            The final state containing the conversation messages and result.
        """
        # Get the compiled graph runner by name
        app = compile("supervisor")

        # Execute the multi-agent system
        # The supervisor will coordinate the specialized agents
        result = await app.ainvoke(
            {"messages": [{"role": "user", "content": request}]}
        )

        return result
