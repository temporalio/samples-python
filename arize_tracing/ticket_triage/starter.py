"""Starter for the ticket triage sample.

Opens one root span around the whole interaction (start workflow, send the
approval update, await the result) so that everything — including the
workflow, activity, and LLM spans produced on the worker — lands in a single
Arize trace. OpenInference trace-level attributes (session, user, input,
output, metadata, tags) are set on this root span; Arize reads a trace's
input and output from its root span.
"""

import argparse
import asyncio
import dataclasses
import json
import os
import uuid

from openinference.semconv.trace import (
    OpenInferenceMimeTypeValues,
    OpenInferenceSpanKindValues,
    SpanAttributes,
)
from opentelemetry import baggage, context, trace
from temporalio.client import Client
from temporalio.contrib.opentelemetry import OpenTelemetryPlugin
from temporalio.envconfig import ClientConfig

from arize_tracing.telemetry import force_flush, setup_tracing, trace_url
from arize_tracing.ticket_triage.activities import ApprovalDecision, Ticket
from arize_tracing.ticket_triage.workflows import TicketTriageWorkflow

TASK_QUEUE = "arize-ticket-triage-task-queue"


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
        "Arize trace still comes out as a single clean tree.",
    )
    parser.add_argument(
        "--workflow-id",
        help="Reuse a workflow ID. Each run of the same ID is a new Temporal run "
        "and a new Arize trace, grouped under one Arize session (the ID).",
    )
    parser.add_argument(
        "--user",
        default=os.environ.get("ARIZE_DEMO_USER", "demo-user"),
        help="Reported as the OpenInference user.id",
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

    # The workflow ID doubles as the Arize session ID, so all traces of one
    # Workflow Execution group together in the Sessions view. A fresh ID per
    # run is the default; --workflow-id reuses one on purpose.
    workflow_id = args.workflow_id or f"ticket-triage-{uuid.uuid4().hex[:8]}"

    ticket = Ticket(
        ticket_id="T-1001",
        customer_email="ada@acme.example",
        subject="Charged twice for the July invoice",
        body=(
            "Hi, my card statement shows two identical charges for our July "
            "invoice. Can you check what happened and refund the duplicate?"
        ),
    )

    # @@@SNIPSTART python-arize-tracing-root-span
    # session.id / user.id as OpenTelemetry baggage: Temporal propagates baggage
    # through its trace-context header, so the enrichment processor can stamp
    # both onto every span on the worker as well, LLM spans included.
    ctx = baggage.set_baggage(SpanAttributes.SESSION_ID, workflow_id)
    ctx = baggage.set_baggage(SpanAttributes.USER_ID, args.user, context=ctx)
    token = context.attach(ctx)
    tracer = trace.get_tracer(__name__)
    try:
        with tracer.start_as_current_span(
            "ticket-triage",
            attributes={
                # OpenInference attributes on the trace's root span: Arize lists
                # the trace by its input/output and groups it by session.
                SpanAttributes.OPENINFERENCE_SPAN_KIND: OpenInferenceSpanKindValues.CHAIN.value,
                SpanAttributes.SESSION_ID: workflow_id,
                SpanAttributes.USER_ID: args.user,
                SpanAttributes.INPUT_VALUE: json.dumps(dataclasses.asdict(ticket)),
                SpanAttributes.INPUT_MIME_TYPE: OpenInferenceMimeTypeValues.JSON.value,
                SpanAttributes.METADATA: json.dumps(
                    {
                        "temporal.workflow_id": workflow_id,
                        "temporal.task_queue": TASK_QUEUE,
                        "temporal.namespace": client.namespace,
                    }
                ),
                SpanAttributes.TAG_TAGS: ["temporal", "ticket-triage"],
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
            root.set_attribute(
                SpanAttributes.OUTPUT_VALUE, json.dumps(dataclasses.asdict(result))
            )
            root.set_attribute(
                SpanAttributes.OUTPUT_MIME_TYPE, OpenInferenceMimeTypeValues.JSON.value
            )
    finally:
        context.detach(token)
        # The starter is short-lived; flush so its spans (the trace root and
        # the client-side StartWorkflow/StartWorkflowUpdate spans) are not
        # dropped at process exit.
        force_flush()
    # @@@SNIPEND

    print(f"Workflow status: {result.status}")
    if result.reply:
        print(f"Drafted reply:\n{result.reply}")
    print(f"Trace ID: {trace_id}")
    print(f"Arize trace: {trace_url(trace_id)}")


if __name__ == "__main__":
    asyncio.run(main())
