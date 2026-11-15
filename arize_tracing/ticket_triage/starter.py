"""Starter for the ticket triage sample.

Opens one root span around the whole interaction (start, approval update,
result) so the worker's workflow, activity, and LLM spans all land in a single
Arize trace. Arize reads a trace's session, user, input, and output from the
OpenInference attributes on this root span.
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

from telemetry import force_flush, setup_tracing, trace_url
from ticket_triage.activities import ApprovalDecision, Ticket
from ticket_triage.workflows import TASK_QUEUE, TicketTriageWorkflow


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--decline", action="store_true", help="Decline the ticket")
    parser.add_argument(
        "--pause-before-approval",
        type=int,
        default=0,
        metavar="SECONDS",
        help="Wait before sending the approval update, so you can kill and "
        "restart the worker while the workflow durably awaits approval.",
    )
    parser.add_argument("--workflow-id", help="Reuse a workflow ID (Arize session)")
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
    config["plugins"] = [OpenTelemetryPlugin(add_temporal_spans=True)]
    client = await Client.connect(**config)

    # The workflow ID doubles as the Arize session ID.
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
    # session.id / user.id as baggage: Temporal carries it in its trace-context
    # header, so the enrichment processor stamps both onto worker spans too.
    ctx = baggage.set_baggage(SpanAttributes.SESSION_ID, workflow_id)
    ctx = baggage.set_baggage(SpanAttributes.USER_ID, args.user, context=ctx)
    token = context.attach(ctx)
    tracer = trace.get_tracer(__name__)
    try:
        with tracer.start_as_current_span(
            "ticket-triage",
            attributes={
                # Arize reads these trace-level attributes from the root span.
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
        force_flush()  # the starter is short-lived; do not drop its spans
    # @@@SNIPEND

    print(f"Workflow status: {result.status}")
    if result.reply:
        print(f"Drafted reply:\n{result.reply}")
    print(f"Trace ID: {trace_id}")
    print(f"Arize trace: {trace_url(trace_id)}")


if __name__ == "__main__":
    asyncio.run(main())
