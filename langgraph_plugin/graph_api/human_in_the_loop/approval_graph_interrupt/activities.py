"""Activities for the approval workflow."""

from temporalio import activity


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
        f"    python -m langgraph_plugin.graph_api.human_in_the_loop.approval_graph_interrupt.run_respond {workflow_id} --approve --reason 'Approved'\n"
        f"    python -m langgraph_plugin.graph_api.human_in_the_loop.approval_graph_interrupt.run_respond {workflow_id} --reject --reason 'Rejected'"
    )

    # In production, you would send actual notification here
    print("\n*** APPROVAL NEEDED ***")
    print(f"Workflow ID: {workflow_id}")
    print(f"Request: {message}")
    print("\nTo respond, run:")
    print(
        f"  Approve: uv run python -m langgraph_plugin.graph_api.human_in_the_loop.approval_graph_interrupt.run_respond {workflow_id} --approve --reason 'Your reason'"
    )
    print(
        f"  Reject:  uv run python -m langgraph_plugin.graph_api.human_in_the_loop.approval_graph_interrupt.run_respond {workflow_id} --reject --reason 'Your reason'"
    )
    print()

    return f"Notification sent for workflow {workflow_id}"
