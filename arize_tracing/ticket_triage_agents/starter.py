"""Starter for the ticket triage agents sample.

The Agents SDK trace opened here becomes the root AGENT span of the Arize trace:
the plugin bridges Agents SDK tracing to OpenTelemetry, so the OpenInference
trace-level attributes (session, user, input, output, metadata, tags) go onto
that span instead of a separate OpenTelemetry root.
"""

import argparse
import asyncio
import dataclasses
import json
import os
import uuid

from agents import trace as agents_trace
from openinference.semconv.trace import OpenInferenceMimeTypeValues, SpanAttributes
from opentelemetry import trace
from temporalio.client import Client
from temporalio.envconfig import ClientConfig

from arize_tracing.telemetry import (
    force_flush,
    quiet_otel_context_detach_errors,
    setup_tracing,
    trace_url,
)
from arize_tracing.ticket_triage.activities import ApprovalDecision, Ticket
from arize_tracing.ticket_triage_agents.plugin import TASK_QUEUE, agents_plugin
from arize_tracing.ticket_triage_agents.workflows import (
    AgentTicketRequest,
    TicketTriageAgentsWorkflow,
)


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

    setup_tracing("ticket-triage-agents-starter")
    quiet_otel_context_detach_errors()
    plugin = agents_plugin()

    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")
    client = await Client.connect(**config, plugins=[plugin])

    workflow_id = args.workflow_id or f"ticket-triage-agents-{uuid.uuid4().hex[:8]}"
    ticket = Ticket(
        ticket_id="T-1001",
        customer_email="ada@acme.example",
        subject="Charged twice for the July invoice",
        body=(
            "Hi, my card statement shows two identical charges for our July "
            "invoice. Can you check what happened and refund the duplicate?"
        ),
    )
    request = AgentTicketRequest(
        ticket=ticket, model=os.environ.get("MODEL_AGENT", "gpt-4o-mini")
    )

    # @@@SNIPSTART python-arize-tracing-agents-starter
    # Starting an Agents SDK trace outside a worker requires the plugin's
    # tracing context. The OpenInference instrumentation turns the trace into
    # the root AGENT span and makes it the current OpenTelemetry span, so the
    # OpenInference trace-level attributes are set on it directly.
    try:
        with plugin.tracing_context():
            with agents_trace("Ticket triage agents", group_id=workflow_id):
                root = trace.get_current_span()
                root.set_attributes(
                    {
                        SpanAttributes.SESSION_ID: workflow_id,
                        SpanAttributes.USER_ID: args.user,
                        SpanAttributes.INPUT_VALUE: json.dumps(
                            dataclasses.asdict(ticket)
                        ),
                        SpanAttributes.INPUT_MIME_TYPE: OpenInferenceMimeTypeValues.JSON.value,
                        SpanAttributes.METADATA: json.dumps(
                            {
                                "temporal.workflow_id": workflow_id,
                                "temporal.task_queue": TASK_QUEUE,
                                "temporal.namespace": client.namespace,
                            }
                        ),
                        SpanAttributes.TAG_TAGS: [
                            "temporal",
                            "ticket-triage",
                            "openai-agents",
                        ],
                    }
                )
                trace_id = format(root.get_span_context().trace_id, "032x")

                handle = await client.start_workflow(
                    TicketTriageAgentsWorkflow.run,
                    request,
                    id=workflow_id,
                    task_queue=TASK_QUEUE,
                )
                print(f"Started workflow: {workflow_id}")
                if args.pause_before_approval:
                    print(f"Pausing {args.pause_before_approval}s before approving ...")
                    await asyncio.sleep(args.pause_before_approval)
                update_result = await handle.execute_update(
                    TicketTriageAgentsWorkflow.approve,
                    ApprovalDecision(approved=approved, reviewer="demo-reviewer"),
                )
                print(f"Approval update: {update_result}")
                result = await handle.result()
                # Set before the Agents SDK trace ends; ending it ends the span.
                root.set_attribute(
                    SpanAttributes.OUTPUT_VALUE, json.dumps(dataclasses.asdict(result))
                )
                root.set_attribute(
                    SpanAttributes.OUTPUT_MIME_TYPE,
                    OpenInferenceMimeTypeValues.JSON.value,
                )
    finally:
        force_flush()
    # @@@SNIPEND

    print(f"Workflow status: {result.status}")
    if result.reply:
        print(f"Drafted reply:\n{result.reply}")
    print(f"Trace ID: {trace_id}")
    print(f"Arize trace: {trace_url(trace_id)}")


if __name__ == "__main__":
    asyncio.run(main())
