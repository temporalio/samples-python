"""ReAct Agent Workflow.

Temporal workflow that executes the ReAct agent with durable execution.

Note: This module only contains the workflow definition. The entrypoint and tasks
are in separate files and are imported by the worker.
"""

from typing import Any

from temporalio import workflow
from temporalio.contrib.langgraph import compile


@workflow.defn
class ReActAgentWorkflow:
    """Temporal workflow that executes a ReAct agent with durable execution.

    This workflow uses the LangGraph Functional API with the Temporal integration.
    Each @task (LLM call, tool execution) runs as a Temporal activity:
    - The call_model task calls the LLM to decide what to do
    - The execute_tools task executes the requested tools

    If any task fails, it is automatically retried. If the worker crashes,
    execution resumes from the last completed task.
    """

    @workflow.run
    async def run(self, query: str) -> dict[str, Any]:
        """Run the ReAct agent to answer a query.

        Args:
            query: The user's question or request.

        Returns:
            The final state containing the conversation messages and result.
        """
        # Get the compiled entrypoint runner by name
        app = compile("react_agent_entrypoint")

        # Execute the agent
        result = await app.ainvoke(query)

        return result
