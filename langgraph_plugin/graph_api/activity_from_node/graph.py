"""Activity from Node - Graph Definition.

This module defines a graph where a node runs in the workflow context
and calls Temporal activities directly.
"""

from datetime import timedelta
from typing import Any

from langgraph.graph import END, START, StateGraph
from typing_extensions import TypedDict

# =============================================================================
# State Definition
# =============================================================================


class ProcessingState(TypedDict, total=False):
    """State for the processing graph."""

    data: str
    validated: bool
    enriched_data: str
    final_result: str


# =============================================================================
# Node Functions
# =============================================================================


async def orchestrator_node(state: ProcessingState) -> ProcessingState:
    """Node that orchestrates multiple activity calls from the workflow.

    This node runs directly in the workflow (run_in_workflow=True) so it can:
    - Call multiple Temporal activities
    - Use workflow features like timers, signals, queries
    - Implement complex orchestration logic

    The node is sandboxed, ensuring deterministic code.
    """
    from temporalio import workflow

    data = state.get("data", "")

    # Call validation activity
    is_valid = await workflow.execute_activity(
        "validate_data",
        data,
        start_to_close_timeout=timedelta(seconds=30),
    )

    if not is_valid:
        return {"validated": False, "final_result": "Validation failed"}

    # Call enrichment activity
    enriched = await workflow.execute_activity(
        "enrich_data",
        data,
        start_to_close_timeout=timedelta(seconds=30),
    )

    return {"validated": True, "enriched_data": enriched}


def finalize_node(state: ProcessingState) -> ProcessingState:
    """Final processing node - runs as a regular activity.

    This demonstrates mixing run_in_workflow nodes with regular activity nodes.
    """
    if not state.get("validated"):
        return state

    enriched = state.get("enriched_data", "")
    return {"final_result": f"Processed: {enriched}"}


# =============================================================================
# Graph Builder
# =============================================================================


def build_activity_from_node_graph() -> Any:
    """Build a graph with a node that calls activities from the workflow.

    The orchestrator node uses run_in_workflow=True to execute directly
    in the workflow context, allowing it to call Temporal activities.
    """
    from temporalio.contrib.langgraph import activity_options, temporal_node_metadata

    graph = StateGraph(ProcessingState)

    # Orchestrator runs in workflow to call activities
    graph.add_node(
        "orchestrator",
        orchestrator_node,
        metadata=temporal_node_metadata(run_in_workflow=True),
    )

    # Finalize runs as a regular activity with timeout config
    graph.add_node(
        "finalize",
        finalize_node,
        metadata=activity_options(
            start_to_close_timeout=timedelta(seconds=30),
        ),
    )

    graph.add_edge(START, "orchestrator")
    graph.add_edge("orchestrator", "finalize")
    graph.add_edge("finalize", END)

    return graph.compile()
