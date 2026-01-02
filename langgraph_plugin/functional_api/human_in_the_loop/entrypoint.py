"""Human-in-the-Loop Entrypoint Definition.

The @entrypoint function demonstrates interrupt() for human approval:
1. Process and validate the request
2. Call interrupt() to pause for human approval
3. Execute based on approval decision
"""

from typing import Any

from langgraph.func import entrypoint
from langgraph.types import interrupt

from langgraph_plugin.functional_api.human_in_the_loop.tasks import (
    execute_action,
    process_request,
)


@entrypoint()
async def approval_entrypoint(
    request_type: str,
    amount: float,
    request_data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run an approval workflow with human-in-the-loop.

    The workflow:
    1. Processes and validates the request
    2. Pauses for human approval using interrupt()
    3. Executes the approved action or rejects

    The interrupt() call pauses the Temporal workflow until a signal
    is received with the human's decision.

    Args:
        request_type: Type of request (e.g., "payment", "refund").
        amount: The monetary amount.
        request_data: Additional request details.

    Returns:
        Dict with final status and execution result.
    """
    request_data = request_data or {}

    # Step 1: Process and validate the request
    validation = await process_request(request_type, amount, request_data)

    # Step 2: Request human approval via interrupt
    # This pauses the workflow and waits for a signal
    approval_request = {
        "request_type": request_type,
        "amount": amount,
        "risk_level": validation["risk_level"],
        "request_data": request_data,
        "message": f"Please approve {request_type} for ${amount:.2f} "
        f"(Risk: {validation['risk_level']})",
    }

    # interrupt() pauses here and returns the human's response when resumed
    approval_response = interrupt(approval_request)

    # Step 3: Execute based on approval
    approved = approval_response.get("approved", False)
    approver = approval_response.get("approver", "unknown")
    reason = approval_response.get("reason", "No reason provided")

    result = await execute_action(
        request_type=request_type,
        amount=amount,
        approved=approved,
        approver=approver,
        reason=reason,
    )

    return {
        "request_type": request_type,
        "amount": amount,
        "risk_level": validation["risk_level"],
        "approved": approved,
        "approver": approver,
        "reason": reason,
        **result,
    }
