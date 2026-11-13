"""Tests for the ticket triage sample.

They run without Arize or an LLM: the LLM activities are mocked (each opens a
span to prove trace context reaches activities), spans go to an in-memory
exporter, and the worker runs with the workflow cache disabled so every
workflow task replays the workflow from the start of history. Asserting the
whole span tree proves spans are emitted exactly once despite replay.
"""

import json
import uuid
from typing import Any, Iterable, Optional

import pytest
from openinference.semconv.trace import OpenInferenceSpanKindValues, SpanAttributes
from opentelemetry import baggage, context, trace
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import StatusCode
from temporalio import activity
from temporalio.client import Client, WorkflowHandle
from temporalio.contrib.opentelemetry import OpenTelemetryPlugin
from temporalio.exceptions import ApplicationError
from temporalio.worker import Replayer, Worker

from telemetry import ACTIVITY_ATTEMPT_ATTRIBUTE, TEMPORAL_SCOPE_PREFIX
from ticket_triage.activities import (
    AccountInfo,
    ApprovalDecision,
    Classification,
    DraftReplyInput,
    Ticket,
)
from ticket_triage.workflows import TicketTriageWorkflow

TICKET = Ticket(
    ticket_id="T-1",
    customer_email="ada@acme.example",
    subject="Charged twice",
    body="Please refund the duplicate charge.",
)
TEST_USER = "test-user"

EXPECTED_APPROVED = [
    "ticket-triage test",
    "  StartWorkflow:TicketTriageWorkflow",
    "    RunWorkflow:TicketTriageWorkflow",
    "      triage",
    "        StartActivity:classify_ticket",
    "          RunActivity:classify_ticket",
    "            mock llm classify",
    "        StartActivity:lookup_account",
    "          RunActivity:lookup_account",
    "            mock account lookup",
    "      StartActivity:draft_reply",
    "        RunActivity:draft_reply",
    "          mock llm draft",
    "  StartWorkflowUpdate:approve",
    "    ValidateUpdate:approve",
    "    HandleUpdate:approve",
]
# Declined tickets never reach draft_reply.
EXPECTED_DECLINED = [line for line in EXPECTED_APPROVED if "draft" not in line]


@activity.defn(name="classify_ticket")
async def classify_ticket_mocked(ticket: Ticket) -> Classification:
    with trace.get_tracer(__name__).start_as_current_span("mock llm classify"):
        return Classification(category="billing", priority="high")


@activity.defn(name="classify_ticket")
async def classify_ticket_fails_once(ticket: Ticket) -> Classification:
    with trace.get_tracer(__name__).start_as_current_span("mock llm classify"):
        if activity.info().attempt == 1:
            raise ApplicationError("simulated transient failure", type="Simulated")
        return Classification(category="billing", priority="high")


@activity.defn(name="lookup_account")
async def lookup_account_mocked(customer_email: str) -> AccountInfo:
    with trace.get_tracer(__name__).start_as_current_span("mock account lookup"):
        return AccountInfo(
            customer_email=customer_email, account_name="Acme Corp", plan="enterprise"
        )


@activity.defn(name="draft_reply")
async def draft_reply_mocked(input: DraftReplyInput) -> str:
    with trace.get_tracer(__name__).start_as_current_span("mock llm draft"):
        return "Sorry about that - refund on the way."


def dump_spans(
    spans: Iterable[ReadableSpan], *, parent_id: Optional[int] = None, depth: int = 0
) -> list[str]:
    """Render spans as an indented tree, one line per span."""
    lines: list[str] = []
    for span in spans:
        if (not span.parent and parent_id is None) or (
            span.parent and span.parent.span_id == parent_id
        ):
            lines.append(f"{'  ' * depth}{span.name}")
            lines += dump_spans(
                spans,
                parent_id=span.context.span_id if span.context else None,
                depth=depth + 1,
            )
    return lines


async def run_workflow(
    client: Client, *, approved: bool = True, classify: Any = classify_ticket_mocked
) -> WorkflowHandle[Any, Any]:
    """Run one interaction the way the starter does.

    The worker's workflow cache is disabled, so every workflow task replays the
    workflow from the start of history.
    """
    config = client.config()
    config["plugins"] = [OpenTelemetryPlugin(add_temporal_spans=True)]
    client = Client(**config)
    workflow_id = f"ticket-triage-test-{uuid.uuid4()}"
    ctx = baggage.set_baggage(SpanAttributes.SESSION_ID, workflow_id)
    ctx = baggage.set_baggage(SpanAttributes.USER_ID, TEST_USER, context=ctx)
    token = context.attach(ctx)
    try:
        async with Worker(
            client,
            task_queue=f"tq-{uuid.uuid4()}",
            workflows=[TicketTriageWorkflow],
            activities=[classify, lookup_account_mocked, draft_reply_mocked],
            max_cached_workflows=0,
        ) as worker:
            with trace.get_tracer(__name__).start_as_current_span(
                "ticket-triage test",
                attributes={
                    SpanAttributes.OPENINFERENCE_SPAN_KIND: OpenInferenceSpanKindValues.CHAIN.value,
                    SpanAttributes.SESSION_ID: workflow_id,
                    SpanAttributes.USER_ID: TEST_USER,
                },
            ):
                handle = await client.start_workflow(
                    TicketTriageWorkflow.run,
                    TICKET,
                    id=workflow_id,
                    task_queue=worker.task_queue,
                )
                await handle.execute_update(
                    TicketTriageWorkflow.approve,
                    ApprovalDecision(approved=approved, reviewer="test-reviewer"),
                )
                await handle.result()
    finally:
        context.detach(token)
    return handle


@pytest.mark.parametrize("approved", [True, False])
async def test_spans_emitted_exactly_once_under_replay_stress(
    client: Client, span_exporter: InMemorySpanExporter, approved: bool
) -> None:
    handle = await run_workflow(client, approved=approved)
    spans = span_exporter.get_finished_spans()
    assert dump_spans(spans) == (EXPECTED_APPROVED if approved else EXPECTED_DECLINED)
    span_ids = [s.context.span_id for s in spans if s.context]
    assert len(set(span_ids)) == len(span_ids)
    assert len({s.context.trace_id for s in spans if s.context}) == 1

    # Replaying the finished workflow's real history must emit zero new spans.
    replayer = Replayer(
        workflows=[TicketTriageWorkflow],
        plugins=[OpenTelemetryPlugin(add_temporal_spans=True)],
    )
    await replayer.replay_workflow(await handle.fetch_history())
    assert len(span_exporter.get_finished_spans()) == len(spans)


async def test_openinference_enrichment(
    client: Client, span_exporter: InMemorySpanExporter
) -> None:
    handle = await run_workflow(client)
    spans = span_exporter.get_finished_spans()
    temporal_spans = [
        s
        for s in spans
        if s.instrumentation_scope
        and s.instrumentation_scope.name.startswith(TEMPORAL_SCOPE_PREFIX)
    ]
    assert len(temporal_spans) == 11  # 1 client start, 1 client update, 9 worker-side

    # Every Temporal span gets an OpenInference kind, the Workflow Id as the
    # Arize session, and the Temporal identifiers as OpenInference metadata.
    for span in temporal_spans:
        attributes = dict(span.attributes or {})
        assert attributes[SpanAttributes.OPENINFERENCE_SPAN_KIND] == "CHAIN", span.name
        assert attributes[SpanAttributes.SESSION_ID] == handle.id, span.name
        assert attributes[SpanAttributes.USER_ID] == TEST_USER, span.name
        metadata = json.loads(str(attributes[SpanAttributes.METADATA]))
        assert metadata["temporalWorkflowID"] == handle.id, span.name

    # One RunActivity span per attempt, each stamped with its attempt number.
    run_activity_spans = [
        s for s in temporal_spans if s.name.startswith("RunActivity:")
    ]
    assert len(run_activity_spans) == 3
    for span in run_activity_spans:
        attributes = dict(span.attributes or {})
        assert attributes[ACTIVITY_ATTEMPT_ATTRIBUTE] == 1
        metadata = json.loads(str(attributes[SpanAttributes.METADATA]))
        assert metadata["temporalActivityAttempt"] == 1

    # Baggage set by the client reaches spans created in workflow and activity
    # code, so Arize can group and filter LLM spans by session and user too.
    for name in (
        "triage",
        "mock llm classify",
        "mock account lookup",
        "mock llm draft",
    ):
        attributes = dict(next(s for s in spans if s.name == name).attributes or {})
        assert attributes[SpanAttributes.SESSION_ID] == handle.id, name
        assert attributes[SpanAttributes.USER_ID] == TEST_USER, name
    triage = next(s for s in spans if s.name == "triage")
    assert (
        dict(triage.attributes or {})[SpanAttributes.OPENINFERENCE_SPAN_KIND] == "CHAIN"
    )


async def test_activity_retry_attempts_are_separate_spans(
    client: Client, span_exporter: InMemorySpanExporter
) -> None:
    await run_workflow(client, classify=classify_ticket_fails_once)
    spans = span_exporter.get_finished_spans()
    # The failed first attempt adds one RunActivity span (with its inner mock
    # span) under the single StartActivity span.
    expected = list(EXPECTED_APPROVED)
    index = expected.index("          RunActivity:classify_ticket")
    expected[index:index] = [
        "          RunActivity:classify_ticket",
        "            mock llm classify",
    ]
    assert dump_spans(spans) == expected

    attempts = [s for s in spans if s.name == "RunActivity:classify_ticket"]
    assert [dict(s.attributes or {})[ACTIVITY_ATTEMPT_ATTRIBUTE] for s in attempts] == [
        1,
        2,
    ]
    assert attempts[0].status.status_code == StatusCode.ERROR
    assert any(event.name == "exception" for event in attempts[0].events)
    assert attempts[1].status.status_code != StatusCode.ERROR
    assert len([s for s in spans if s.name == "StartActivity:classify_ticket"]) == 1
