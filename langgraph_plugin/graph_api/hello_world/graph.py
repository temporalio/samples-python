"""Hello World LangGraph Graph Definition.

This module defines the graph structure and node functions.
It is imported only by the worker (not by the workflow).
"""

from datetime import timedelta
from typing import Any

from langgraph.graph import END, START, StateGraph
from temporalio.contrib.langgraph import activity_options
from typing_extensions import TypedDict

# =============================================================================
# State Definition
# =============================================================================


class HelloState(TypedDict, total=False):
    """Simple state for the hello world agent."""

    query: str
    result: str


# =============================================================================
# Node Functions
# =============================================================================


def process_query(state: HelloState) -> HelloState:
    """Process the query and return a result.

    In a real application, this could call an LLM, database, or external API.
    Each node function runs as a Temporal activity with automatic retries.
    """
    query = state.get("query", "")
    return {"result": f"Processed: {query}"}


# =============================================================================
# Graph Builder
# =============================================================================


def build_hello_graph() -> Any:
    """Build a minimal single-node graph.

    This function is registered with LangGraphPlugin and called to create
    the compiled graph when needed.
    """
    graph = StateGraph(HelloState)

    # Add a single processing node with activity options
    graph.add_node(
        "process",
        process_query,
        metadata=activity_options(
            start_to_close_timeout=timedelta(seconds=30),
        ),
    )

    # Define edges: START -> process -> END
    graph.add_edge(START, "process")
    graph.add_edge("process", END)

    return graph.compile()
