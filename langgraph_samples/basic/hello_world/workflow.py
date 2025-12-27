"""Hello World LangGraph Workflow.

Minimal example demonstrating LangGraph with Temporal integration.

Note: This module only contains the workflow definition. The graph definition
is in graph.py and is only imported by the worker (not by this workflow module).
This separation is required because langgraph cannot be imported in the
workflow sandbox.
"""

from typing import Any

from temporalio import workflow
from temporalio.contrib.langgraph import compile


@workflow.defn
class HelloWorldWorkflow:
    """Temporal workflow that executes the hello world LangGraph agent.

    This workflow demonstrates:
    - Using compile() to get a graph runner by name
    - Executing the graph with ainvoke()
    - Each node runs as a Temporal activity with durability guarantees
    """

    @workflow.run
    async def run(self, query: str) -> dict[str, Any]:
        """Run the hello world agent.

        Args:
            query: The input query to process.

        Returns:
            The final state containing the processed result.
        """
        # Get the compiled graph runner by name
        app = compile("hello_graph")

        # Execute the graph - the "process" node runs as a Temporal activity
        result = await app.ainvoke({"query": query})

        return result
