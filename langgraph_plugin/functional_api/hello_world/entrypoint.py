"""Hello World Entrypoint Definition.

The @entrypoint function runs directly in the Temporal workflow sandbox.
It must be deterministic - non-deterministic operations belong in @task functions.
"""

from typing import Any

from langgraph.func import entrypoint

from langgraph_plugin.functional_api.hello_world.tasks import process_query


@entrypoint()
async def hello_world_entrypoint(query: str) -> dict[str, Any]:
    """Simple hello world entrypoint.

    Demonstrates:
    - Single task execution
    - Task result handling

    Args:
        query: The input query to process.

    Returns:
        Dict containing the query and processed result.
    """
    # Task call becomes a Temporal activity
    result = await process_query(query)

    return {
        "query": query,
        "result": result,
    }
