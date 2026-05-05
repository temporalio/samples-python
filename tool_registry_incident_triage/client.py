"""Client CLI for the Python triage workers.

Usage:
  python -m client pending                       # list pending approval workflows
  python -m client approve <workflow-id> <reason>
  python -m client reject  <workflow-id> <reason>
  python -m client trigger <alertname> <service> # post a synthetic alert (skips webhook)
"""
from __future__ import annotations

import asyncio
import os
import sys
from datetime import datetime, timezone

from temporalio.client import Client

from approval_workflow import ApprovalWorkflow
from triage_workflow import IncidentTriageWorkflow
from triage_types import AlertPayload, ApprovalResponse


async def make_client() -> Client:
    address = os.environ["TEMPORAL_ADDRESS"]
    namespace = os.environ["TEMPORAL_NAMESPACE"]
    api_key = os.environ["TEMPORAL_API_KEY"]
    return await Client.connect(
        address,
        namespace=namespace,
        rpc_metadata={"authorization": f"Bearer {api_key}"},
        tls=True,
    )


async def pending() -> None:
    client = await make_client()
    any_found = False
    async for wf in client.list_workflows(
        'WorkflowType="approvalWorkflow" AND ExecutionStatus="Running"'
    ):
        any_found = True
        handle = client.get_workflow_handle(wf.id)
        try:
            req = await handle.query("pending-approval")
        except Exception:  # noqa: BLE001
            req = None
        print(f"\n{wf.id} (started {wf.start_time})")
        if req:
            print(f"  message:   {req.message}")
            print(f"  diagnosis: {req.diagnosis}")
            print(f"  proposed:  {req.proposedAction}")
            print(f"  approve:   python -m client approve {wf.id} \"<reason>\"")
            print(f"  reject:    python -m client reject  {wf.id} \"<reason>\"")
        else:
            print("  (workflow exists but agent has not requested approval yet)")
    if not any_found:
        print("(no pending approval workflows)")


async def decide(decision: str, workflow_id: str, reason: str) -> None:
    client = await make_client()
    handle = client.get_workflow_handle(workflow_id)
    response = ApprovalResponse(decision=decision, reason=reason)  # type: ignore[arg-type]
    await handle.signal("approval-decision", response)
    print(f"signaled {workflow_id}: {decision} — {reason}")


async def trigger(alertname: str, service: str) -> None:
    client = await make_client()
    task_queue = os.environ.get("TEMPORAL_TASK_QUEUE", "triage-python")
    workflow_id = f"triage-{alertname.lower()}-{service.lower()}"
    alert = AlertPayload(
        status="firing",
        labels={"alertname": alertname, "service": service, "severity": "critical", "runbook": "synthetic"},
        annotations={
            "summary": f"Synthetic test alert for {service}",
            "description": "Triggered manually via client.py to exercise the triage flow.",
        },
        startsAt=datetime.now(timezone.utc).isoformat(),
    )
    handle = await client.start_workflow(
        IncidentTriageWorkflow.run,
        alert,
        id=workflow_id,
        task_queue=task_queue,
        start_signal="alert-update",
        start_signal_args=[alert],
    )
    print(f"started triage workflow: {handle.id} on {task_queue}")


def main() -> None:
    args = sys.argv[1:]
    if not args:
        print("Usage: python -m client <pending|approve|reject|trigger> ...", file=sys.stderr)
        sys.exit(1)

    cmd = args[0]
    if cmd == "pending":
        asyncio.run(pending())
    elif cmd == "approve":
        if len(args) < 3:
            print("Usage: python -m client approve <wfid> <reason>", file=sys.stderr); sys.exit(1)
        asyncio.run(decide("approved", args[1], " ".join(args[2:])))
    elif cmd == "reject":
        if len(args) < 3:
            print("Usage: python -m client reject <wfid> <reason>", file=sys.stderr); sys.exit(1)
        asyncio.run(decide("rejected", args[1], " ".join(args[2:])))
    elif cmd == "trigger":
        if len(args) < 3:
            print("Usage: python -m client trigger <alertname> <service>", file=sys.stderr); sys.exit(1)
        asyncio.run(trigger(args[1], args[2]))
    else:
        print(f"Unknown command: {cmd}", file=sys.stderr); sys.exit(1)


if __name__ == "__main__":
    main()
