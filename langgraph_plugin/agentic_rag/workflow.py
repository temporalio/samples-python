"""Agentic RAG Workflow.

Temporal workflow that executes the agentic RAG agent with durable execution.

Note: This module only contains the workflow definition. The graph definition
is in graph.py and is only imported by the worker (not by this workflow module).
This separation is required because LangGraph cannot be imported in the
workflow sandbox.
"""

from typing import Any

from temporalio import workflow
from temporalio.contrib.langgraph import compile


@workflow.defn
class AgenticRAGWorkflow:
    """Temporal workflow that executes an agentic RAG agent.

    This workflow uses a LangGraph graph that intelligently decides:
    - Whether to retrieve documents or respond directly
    - If retrieved documents are relevant (with grading)
    - Whether to rewrite the query for better retrieval

    Each graph node runs as a Temporal activity:
    - The "agent" node decides whether to retrieve
    - The "retrieve" node fetches documents
    - The "generate" node produces answers
    - The "rewrite" node reformulates queries

    If any node fails, it is automatically retried. If the worker crashes,
    execution resumes from the last completed node.
    """

    @workflow.run
    async def run(self, query: str) -> dict[str, Any]:
        """Run the agentic RAG agent to answer a query.

        The agent will:
        1. Decide if retrieval is needed based on the query
        2. Retrieve relevant documents if needed
        3. Grade documents for relevance
        4. Generate answer or rewrite query as appropriate

        Args:
            query: The user's question or request.

        Returns:
            The final state containing the conversation messages and result.
        """
        # Get the compiled graph runner by name
        app = compile("agentic_rag")

        # Execute the agent
        # The input format is a dict with "messages"
        result = await app.ainvoke({"messages": [{"role": "user", "content": query}]})

        return result
