"""Hello World Task Definitions.

Tasks are @task-decorated functions that run as Temporal activities.
They can contain non-deterministic operations (API calls, I/O, randomness).
"""

from langgraph.func import task


@task
def process_query(query: str) -> str:
    """Process the query and return a result.

    In a real application, this could call an LLM, database, or external API.
    Each @task runs as a Temporal activity with automatic retries.

    Args:
        query: The input query to process.

    Returns:
        The processed result string.
    """
    return f"Processed: {query}"
