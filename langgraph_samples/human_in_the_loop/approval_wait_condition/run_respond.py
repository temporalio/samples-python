"""Respond to an approval request (Condition-based).

This script allows an approver to approve or reject a pending approval workflow.
"""

import argparse
import asyncio

from temporalio.client import Client
from temporalio.envconfig import ClientConfig

from langgraph_samples.human_in_the_loop.approval_wait_condition.workflow import (
    ApprovalWorkflow,
)


async def main() -> None:
    parser = argparse.ArgumentParser(description="Respond to an approval workflow")
    parser.add_argument("workflow_id", help="The workflow ID to respond to")
    parser.add_argument("--approve", action="store_true", help="Approve the request")
    parser.add_argument("--reject", action="store_true", help="Reject the request")
    parser.add_argument("--status", action="store_true", help="Check workflow status")
    parser.add_argument("--reason", default="", help="Reason for approval/rejection")
    parser.add_argument(
        "--approver", default="cli-user", help="Approver identifier (default: cli-user)"
    )

    args = parser.parse_args()

    # Validate arguments
    if not args.status and not args.approve and not args.reject:
        parser.error("Must specify --approve, --reject, or --status")
    if args.approve and args.reject:
        parser.error("Cannot specify both --approve and --reject")

    # Connect to Temporal
    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")
    client = await Client.connect(**config)

    # Get workflow handle
    handle = client.get_workflow_handle(args.workflow_id)

    if args.status:
        # Query the workflow status
        try:
            status = await handle.query(ApprovalWorkflow.get_status)
            pending = await handle.query(ApprovalWorkflow.get_pending_approval)
            print(f"Workflow ID: {args.workflow_id}")
            print(f"Status: {status}")
            if pending:
                print(f"Pending approval: {pending.get('message', 'No message')}")
                print(f"  Request type: {pending.get('request_type')}")
                print(f"  Amount: ${pending.get('amount', 0):.2f}")
                print(f"  Risk level: {pending.get('risk_level')}")
        except Exception as e:
            print(f"Error querying workflow: {e}")
    else:
        # Send approval/rejection signal
        approved = args.approve
        response = {
            "approved": approved,
            "reason": args.reason,
            "approver": args.approver,
        }

        try:
            await handle.signal(ApprovalWorkflow.provide_approval, response)
            action = "Approved" if approved else "Rejected"
            print(f"{action} workflow {args.workflow_id}")
            if args.reason:
                print(f"Reason: {args.reason}")
        except Exception as e:
            print(f"Error sending signal: {e}")


if __name__ == "__main__":
    asyncio.run(main())
