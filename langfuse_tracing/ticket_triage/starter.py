"""Starter for the ticket triage sample.

Opens one root span around the whole interaction (start workflow, send the
approval update, await the result) so that everything — including the
workflow, activity, and LLM spans produced on the worker — lands in a single
Langfuse trace. Langfuse trace-level attributes (name, session, user, tags)
are set on this root span.
"""

import argparse
import asyncio
import os
import uuid

from opentelemetry import trace
from temporalio.client import Client
from temporalio.contrib.opentelemetry import OpenTelemetryPlugin
from temporalio.envconfig import ClientConfig

from langfuse_tracing.telemetry import force_flush, setup_tracing
from langfuse_tracing.ticket_triage.activities import ApprovalDecision, Ticket
from langfuse_tracing.ticket_triage.workflows import TicketTriageWorkflow

TASK_QUEUE = "langfuse-ticket-triage-task-queue"


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--decline", action="store_true", help="Decline the ticket")
    parser.add_argument(
        "--pause-before-approval",
        type=int,
        default=0,
        metavar="SECONDS",
        help="Wait before sending the approval update. While the workflow durably "
        "awaits approval you can kill and restart the worker to see that the "
        "Langfuse trace still comes out as a single clean tree.",
    )
    args = parser.parse_args()
    approved = not args.decline

    setup_tracing("ticket-triage-starter")

    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")
    client = await Client.connect(
        **config,
        plugins=[OpenTelemetryPlugin(add_temporal_spans=True)],
    )

    # A fresh workflow ID per run avoids Temporal workflow ID conflicts and
    # gives each run its own Langfuse session (langfuse.session.id on the root
    # span below). The trace itself is keyed by the root span's trace ID,
    # which is new on every run.
    workflow_id = f"ticket-triage-{uuid.uuid4().hex[:8]}"

    ticket = Ticket(
        ticket_id="T-1001",
        customer_email="ada@acme.example",
        subject="Charged twice for the July invoice",
        body=(
            "Hi, my card statement shows two identical charges for our July "
            "invoice. Can you check what happened and refund the duplicate?"
        ),
    )

    tracer = trace.get_tracer(__name__)
    try:
        with tracer.start_as_current_span(
            "ticket-triage",
            attributes={
                # langfuse.* attributes on the trace's root span set Langfuse
                # trace-level fields, enabling filtering by session/user/tags.
                "langfuse.trace.name": "ticket-triage",
                "langfuse.session.id": workflow_id,
                "langfuse.user.id": os.environ.get("LANGFUSE_DEMO_USER", "demo-user"),
                "langfuse.trace.tags": ["temporal", "ticket-triage"],
                "langfuse.trace.metadata.temporal_workflow_id": workflow_id,
            },
        ) as root:
            trace_id = format(root.get_span_context().trace_id, "032x")
            handle = await client.start_workflow(
                TicketTriageWorkflow.run,
                ticket,
                id=workflow_id,
                task_queue=TASK_QUEUE,
            )
            print(f"Started workflow: {workflow_id}")

            if args.pause_before_approval:
                print(f"Pausing {args.pause_before_approval}s before approving ...")
                await asyncio.sleep(args.pause_before_approval)

            update_result = await handle.execute_update(
                TicketTriageWorkflow.approve,
                ApprovalDecision(approved=approved, reviewer="demo-reviewer"),
            )
            print(f"Approval update: {update_result}")

            result = await handle.result()

        print(f"Workflow status: {result.status}")
        if result.reply:
            print(f"Drafted reply:\n{result.reply}")

        host = os.environ.get("LANGFUSE_HOST", "http://localhost:3000").rstrip("/")
        # The UI link needs the Langfuse project ID; the default matches the
        # project provisioned by langfuse_tracing/langfuse/docker-compose.yml.
        project = os.environ.get("LANGFUSE_PROJECT_ID", "langfuse-tracing-demo")
        print(f"Trace ID: {trace_id}")
        print(f"Langfuse trace: {host}/project/{project}/traces/{trace_id}")
    finally:
        # The starter is short-lived; flush so its spans (the trace root and
        # the client-side StartWorkflow/StartWorkflowUpdate spans) are not
        # dropped at process exit.
        force_flush()


if __name__ == "__main__":
    asyncio.run(main())
