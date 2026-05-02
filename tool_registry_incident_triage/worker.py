"""Temporal worker for the Python triage workflow.

Connects to Temporal Cloud, polls the task queue from TEMPORAL_TASK_QUEUE
(typically `triage-python`), registers IncidentTriageWorkflow + ApprovalWorkflow
+ the triage activity.
"""
from __future__ import annotations

import asyncio
import os
import sys

from temporalio.client import Client
from temporalio.worker import Worker

from approval_workflow import ApprovalWorkflow
from triage_activity import triage_incident_activity
from triage_workflow import IncidentTriageWorkflow


async def main() -> None:
    address = os.environ.get("TEMPORAL_ADDRESS")
    namespace = os.environ.get("TEMPORAL_NAMESPACE")
    api_key = os.environ.get("TEMPORAL_API_KEY")
    task_queue = os.environ.get("TEMPORAL_TASK_QUEUE", "triage-python")

    if not (address and namespace and api_key):
        print("Missing TEMPORAL_ADDRESS / TEMPORAL_NAMESPACE / TEMPORAL_API_KEY", file=sys.stderr)
        sys.exit(1)

    print(f"connecting to {address} (ns={namespace}) on task queue {task_queue}")

    client = await Client.connect(
        address,
        namespace=namespace,
        rpc_metadata={"authorization": f"Bearer {api_key}"},
        tls=True,
    )

    worker = Worker(
        client,
        task_queue=task_queue,
        workflows=[IncidentTriageWorkflow, ApprovalWorkflow],
        activities=[triage_incident_activity],
    )

    print(f"worker ready — polling {task_queue}")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
