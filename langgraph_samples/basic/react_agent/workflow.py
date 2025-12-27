"""ReAct Agent Workflow.

Temporal workflow that executes the ReAct agent with durable execution.

Note: This module only contains the workflow definition. The graph definition
is in graph.py and is only imported by the worker (not by this workflow module).
This separation is required because LangGraph cannot be imported in the
workflow sandbox.
"""

from typing import Any

from temporalio import workflow
from temporalio.contrib.langgraph import compile


@workflow.defn
class ReActAgentWorkflow:
    """Temporal workflow that executes a ReAct agent with fully durable execution.

    This workflow demonstrates:
    - Using temporal_model() to wrap the LLM for durable calls
    - Using temporal_tool() for durable tool execution
    - The think-act-observe loop pattern (ReAct)

    Both LLM calls and tool invocations run as Temporal activities,
    providing automatic retries, failure recovery, and replay safety.
    """

    @workflow.run
    async def run(self, query: str) -> dict[str, Any]:
        """Run the ReAct agent to answer a query.

        The agent will:
        1. Think about what information is needed
        2. Use tools to gather information
        3. Synthesize a final answer

        Args:
            query: The user's question or request.

        Returns:
            The final state containing the conversation messages and result.
        """
        # Get the compiled graph runner by name
        app = compile("react_agent")

        # Execute the agent
        # The input format for create_react_agent is a dict with "messages"
        result = await app.ainvoke(
            {"messages": [{"role": "user", "content": query}]}
        )

        return result
