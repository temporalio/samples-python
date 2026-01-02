"""Task definitions for the Human-in-the-Loop workflow.

Each @task runs as a Temporal activity with automatic retries.
Demonstrates interrupt() for human approval patterns.
"""

from typing import Any

from langgraph.func import task


@task
def process_request(
    request_type: str, amount: float, request_data: dict[str, Any]
) -> dict[str, Any]:
    """Validate and assess the request before approval.

    Args:
        request_type: Type of request (e.g., "payment", "refund").
        amount: The monetary amount.
        request_data: Additional request details.

    Returns:
        Dict with validation status and risk assessment.
    """
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
        "amount": amount,
        "request_type": request_type,
    }


@task
def execute_action(
    request_type: str,
    amount: float,
    approved: bool,
    approver: str,
    reason: str,
) -> dict[str, Any]:
    """Execute or reject the action based on approval status.

    Args:
        request_type: Type of request.
        amount: The monetary amount.
        approved: Whether the request was approved.
        approver: Who approved/rejected.
        reason: Reason for the decision.

    Returns:
        Dict with execution result.
    """
    if approved:
        return {
            "executed": True,
            "result": f"Successfully processed {request_type} for ${amount:.2f}. "
            f"Approved by {approver}: {reason}",
        }
    else:
        return {
            "executed": False,
            "result": f"Request rejected by {approver}: {reason}",
        }
