"""Activity from Node - Workflow Definition.

Demonstrates calling Temporal activities from a LangGraph node.

Note: This module only contains the workflow definition. The graph and
activities are defined separately and imported only by the worker.
"""

from typing import Any

from temporalio import workflow
from temporalio.contrib.langgraph import compile


@workflow.defn
class ActivityFromNodeWorkflow:
    """Workflow that runs a graph with activity-calling nodes.

    This demonstrates:
    - Using run_in_workflow=True for nodes that need workflow context
    - Calling Temporal activities from within graph nodes
    - Mixing run_in_workflow nodes with regular activity nodes
    """

    @workflow.run
    async def run(self, data: str) -> dict[str, Any]:
        """Run the processing graph.

        Args:
            data: The input data to process.

        Returns:
            The final state with processing results.
        """
        app = compile("activity_from_node_graph")

        result = await app.ainvoke({"data": data})

        return result
