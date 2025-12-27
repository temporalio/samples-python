"""Approval Workflow Graph Definition.

This module builds a graph that demonstrates human-in-the-loop approval
using LangGraph's interrupt() function.

The graph flow:
1. process_request: Validates and prepares the request
2. request_approval: Calls interrupt() to pause for human approval
3. execute_action: Processes the approved request (or rejects it)
"""

from typing import Any

from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt
from typing_extensions import TypedDict


class ApprovalState(TypedDict, total=False):
    """State for the approval workflow."""

    # Input
    request_type: str
    request_data: dict[str, Any]
    amount: float

    # Processing state
    validated: bool
    risk_level: str

    # Approval state
    approved: bool
    approval_reason: str
    approver: str

    # Output
    result: str
    executed: bool


def process_request(state: ApprovalState) -> ApprovalState:
    """Validate and assess the request before approval.

    This node analyzes the request and determines risk level.
    """
    amount = state.get("amount", 0)

    # Determine risk level based on amount
    if amount < 100:
        risk_level = "low"
    elif amount < 1000:
        risk_level = "medium"
    else:
        risk_level = "high"

    return {
        "validated": True,
        "risk_level": risk_level,
    }


def request_approval(state: ApprovalState) -> ApprovalState:
    """Request human approval via interrupt.

    This node pauses execution and waits for human input.
    The interrupt() call returns the human's response when resumed.
    """
    # Create the approval request with context for the human
    approval_request = {
        "request_type": state.get("request_type", "unknown"),
        "amount": state.get("amount", 0),
        "risk_level": state.get("risk_level", "unknown"),
        "request_data": state.get("request_data", {}),
        "message": f"Please approve {state.get('request_type', 'request')} "
        f"for ${state.get('amount', 0):.2f} (Risk: {state.get('risk_level', 'unknown')})",
    }

    # This pauses the graph and returns control to the workflow.
    # The workflow will wait for a signal with the human's response.
    # When resumed with Command(resume=response), interrupt() returns that response.
    approval_response = interrupt(approval_request)

    return {
        "approved": approval_response.get("approved", False),
        "approval_reason": approval_response.get("reason", ""),
        "approver": approval_response.get("approver", "unknown"),
    }


def execute_action(state: ApprovalState) -> ApprovalState:
    """Execute or reject the action based on approval status."""
    if state.get("approved"):
        return {
            "executed": True,
            "result": f"Successfully processed {state.get('request_type', 'request')} "
            f"for ${state.get('amount', 0):.2f}. "
            f"Approved by {state.get('approver', 'unknown')}: {state.get('approval_reason', '')}",
        }
    else:
        return {
            "executed": False,
            "result": f"Request rejected by {state.get('approver', 'unknown')}: "
            f"{state.get('approval_reason', 'No reason provided')}",
        }


def build_approval_graph() -> Any:
    """Build the approval workflow graph.

    Flow:
    START -> process_request -> request_approval -> execute_action -> END

    The request_approval node uses interrupt() to pause for human input.
    """
    graph = StateGraph(ApprovalState)

    # Add nodes
    graph.add_node("process_request", process_request)
    graph.add_node("request_approval", request_approval)
    graph.add_node("execute_action", execute_action)

    # Define edges
    graph.add_edge(START, "process_request")
    graph.add_edge("process_request", "request_approval")
    graph.add_edge("request_approval", "execute_action")
    graph.add_edge("execute_action", END)

    return graph.compile()
