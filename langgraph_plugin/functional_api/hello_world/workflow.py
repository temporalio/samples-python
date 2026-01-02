"""Hello World LangGraph Functional API Workflow.

Minimal example demonstrating LangGraph Functional API with Temporal integration.

Note: This module only contains the workflow definition. The entrypoint and tasks
are in separate files and are imported by the worker.
"""

from typing import Any

from temporalio import workflow
from temporalio.contrib.langgraph import compile_functional


@workflow.defn
class HelloWorldWorkflow:
    """Temporal workflow that executes the hello world LangGraph entrypoint.

    This workflow demonstrates:
    - Using compile_functional() to get an entrypoint runner by name
    - Executing the entrypoint with ainvoke()
    - Each @task runs as a Temporal activity with durability guarantees
    """

    @workflow.run
    async def run(self, query: str) -> dict[str, Any]:
        """Run the hello world entrypoint.

        Args:
            query: The input query to process.

        Returns:
            The final state containing the processed result.
        """
        # Get the compiled entrypoint runner by name
        app = compile_functional("hello_world_entrypoint")

        # Execute the entrypoint - the "process_query" task runs as a Temporal activity
        result = await app.ainvoke(query)

        return result
