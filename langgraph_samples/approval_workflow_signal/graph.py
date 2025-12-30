"""Approval Workflow Graph Definition (Signal-based).

This module builds a graph that demonstrates human-in-the-loop approval
using run_in_workflow=True to access Temporal signals directly.

The graph flow:
1. process_request: Validates and prepares the request
2. request_approval: Uses run_in_workflow=True to wait for Temporal signal
3. execute_action: Processes the approved request (or rejects it)
"""

from datetime import timedelta
from typing import Any

from langgraph.graph import END, START, StateGraph
from temporalio import activity, workflow
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


@activity.defn
async def notify_approver(request_info: dict) -> str:
    """Notify the approver about a pending approval request.

    In a real implementation, this could:
    - Send an email
    - Post to Slack
    - Create a ticket in a ticketing system
    - Send a push notification

    Args:
        request_info: Information about the approval request.

    Returns:
        Confirmation message.
    """
    workflow_id = activity.info().workflow_id
    message = request_info.get("message", "Approval needed")

    # Log notification (simulating sending notification)
    activity.logger.info(
        f"NOTIFICATION: {message}\n"
        f"  Workflow ID: {workflow_id}\n"
        f"  To respond, run:\n"
        f"    python -m langgraph_samples.approval_workflow_signal.run_respond {workflow_id} --approve --reason 'Approved'\n"
        f"    python -m langgraph_samples.approval_workflow_signal.run_respond {workflow_id} --reject --reason 'Rejected'"
    )

    # In production, you would send actual notification here
    print("\n*** APPROVAL NEEDED ***")
    print(f"Workflow ID: {workflow_id}")
    print(f"Request: {message}")
    print("\nTo respond, run:")
    print(
        f"  Approve: uv run python -m langgraph_samples.approval_workflow_signal.run_respond {workflow_id} --approve --reason 'Your reason'"
    )
    print(
        f"  Reject:  uv run python -m langgraph_samples.approval_workflow_signal.run_respond {workflow_id} --reject --reason 'Your reason'"
    )
    print()

    return f"Notification sent for workflow {workflow_id}"


async def request_approval(state: ApprovalState) -> ApprovalState:
    """Request human approval using Temporal signals directly.

    This node runs inside the workflow (run_in_workflow=True) and can
    access Temporal operations directly via workflow.instance().

    It waits for an approval signal using workflow.wait_condition().
    """
    # Get access to the workflow instance
    wf = workflow.instance()

    # Create the approval request with context for the human
    approval_request = {
        "request_type": state.get("request_type", "unknown"),
        "amount": state.get("amount", 0),
        "risk_level": state.get("risk_level", "unknown"),
        "request_data": state.get("request_data", {}),
        "message": f"Please approve {state.get('request_type', 'request')} "
        f"for ${state.get('amount', 0):.2f} (Risk: {state.get('risk_level', 'unknown')})",
    }

    # Store approval request for queries
    wf._pending_approval = approval_request

    workflow.logger.info("Workflow paused for approval: %s", approval_request["message"])

    # Notify the approver via activity
    await workflow.execute_activity(
        notify_approver,
        approval_request,
        start_to_close_timeout=timedelta(seconds=30),
    )

    # Wait for approval signal
    await workflow.wait_condition(lambda: wf._approval_response is not None)

    approval_response = wf._approval_response

    workflow.logger.info(
        "Received approval response: approved=%s",
        approval_response.get("approved") if approval_response else None,
    )

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

    The request_approval node uses run_in_workflow=True to access
    Temporal operations directly (signals, activities, etc.).
    """
    graph = StateGraph(ApprovalState)

    # Add nodes
    graph.add_node("process_request", process_request)
    # Mark request_approval as run_in_workflow - it can access Temporal operations
    graph.add_node("request_approval", request_approval, metadata={"run_in_workflow": True})
    graph.add_node("execute_action", execute_action)

    # Define edges
    graph.add_edge(START, "process_request")
    graph.add_edge("process_request", "request_approval")
    graph.add_edge("request_approval", "execute_action")
    graph.add_edge("execute_action", END)

    return graph.compile()
