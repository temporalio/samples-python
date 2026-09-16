"""Tests for the ticket triage sample.

These run without Arize or an LLM: the LLM activities are mocked (each opens a
custom span to prove trace context propagates into activities) and spans are
captured with an in-memory exporter. The worker runs with the workflow cache
disabled, so every workflow task replays the workflow from the start of
history — asserting the whole span tree with deep equality proves spans are
emitted exactly once despite replay.
"""

import json
import uuid
from typing import Any, Sequence

import opentelemetry.trace
from openinference.semconv.trace import OpenInferenceSpanKindValues, SpanAttributes
from opentelemetry import baggage, context, trace
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import StatusCode
from temporalio import activity
from temporalio.client import Client, WorkflowHandle
from temporalio.contrib.opentelemetry import OpenTelemetryPlugin, create_tracer_provider
from temporalio.exceptions import ApplicationError
from temporalio.worker import Replayer, Worker

from arize_tracing.telemetry import (
    ACTIVITY_ATTEMPT_ATTRIBUTE,
    TEMPORAL_SCOPE_PREFIX,
    OpenInferenceEnrichmentProcessor,
)
from arize_tracing.ticket_triage.activities import (
    AccountInfo,
    ApprovalDecision,
    Classification,
    DraftReplyInput,
    Ticket,
)
from arize_tracing.ticket_triage.workflows import TicketTriageWorkflow
from tests.arize_tracing.helpers import dump_spans

TICKET = Ticket(
    ticket_id="T-1",
    customer_email="ada@acme.example",
    subject="Charged twice",
    body="Please refund the duplicate charge.",
)
TEST_USER = "test-user"


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


def _install_in_memory_exporter() -> InMemorySpanExporter:
    exporter = InMemorySpanExporter()
    provider = create_tracer_provider()
    provider.add_span_processor(OpenInferenceEnrichmentProcessor())
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    opentelemetry.trace.set_tracer_provider(provider)
    return exporter


def _client_with_plugin(client: Client) -> Client:
    config = client.config()
    config["plugins"] = [OpenTelemetryPlugin(add_temporal_spans=True)]
    return Client(**config)


async def _run_interaction(
    client: Client, task_queue: str, workflow_id: str, approved: bool
) -> WorkflowHandle[Any, Any]:
    """Mirror the starter: baggage + a root span around start, update, result."""
    ctx = baggage.set_baggage(SpanAttributes.SESSION_ID, workflow_id)
    ctx = baggage.set_baggage(SpanAttributes.USER_ID, TEST_USER, context=ctx)
    token = context.attach(ctx)
    try:
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
                task_queue=task_queue,
            )
            await handle.execute_update(
                TicketTriageWorkflow.approve,
                ApprovalDecision(approved=approved, reviewer="test-reviewer"),
            )
            await handle.result()
    finally:
        context.detach(token)
    return handle


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


def _temporal_spans(spans: Sequence[ReadableSpan]) -> list[ReadableSpan]:
    return [
        s
        for s in spans
        if s.instrumentation_scope
        and s.instrumentation_scope.name.startswith(TEMPORAL_SCOPE_PREFIX)
    ]


async def test_spans_emitted_exactly_once_under_replay_stress(
    client: Client, reset_otel_tracer_provider: Any
) -> None:
    exporter = _install_in_memory_exporter()
    new_client = _client_with_plugin(client)
    task_queue = f"tq-{uuid.uuid4()}"
    workflow_id = f"ticket-triage-test-{uuid.uuid4()}"

    async with Worker(
        new_client,
        task_queue=task_queue,
        workflows=[TicketTriageWorkflow],
        activities=[classify_ticket_mocked, lookup_account_mocked, draft_reply_mocked],
        # Disable the workflow cache: every workflow task replays the workflow
        # from the start of history. Tracing must still emit each span once.
        max_cached_workflows=0,
    ):
        handle = await _run_interaction(
            new_client, task_queue, workflow_id, approved=True
        )

    spans = exporter.get_finished_spans()
    assert dump_spans(spans) == EXPECTED_APPROVED
    span_ids = [s.context.span_id for s in spans if s.context]
    assert len(set(span_ids)) == len(span_ids)
    trace_ids = {s.context.trace_id for s in spans if s.context}
    assert len(trace_ids) == 1

    # Replaying the finished workflow's real history must emit zero new spans.
    history = await handle.fetch_history()
    before = len(exporter.get_finished_spans())
    replayer = Replayer(
        workflows=[TicketTriageWorkflow],
        plugins=[OpenTelemetryPlugin(add_temporal_spans=True)],
    )
    await replayer.replay_workflow(history)
    assert len(exporter.get_finished_spans()) == before


async def test_declined_path_span_tree(
    client: Client, reset_otel_tracer_provider: Any
) -> None:
    exporter = _install_in_memory_exporter()
    new_client = _client_with_plugin(client)
    task_queue = f"tq-{uuid.uuid4()}"

    async with Worker(
        new_client,
        task_queue=task_queue,
        workflows=[TicketTriageWorkflow],
        activities=[classify_ticket_mocked, lookup_account_mocked, draft_reply_mocked],
        max_cached_workflows=0,
    ):
        await _run_interaction(
            new_client, task_queue, f"ticket-triage-test-{uuid.uuid4()}", approved=False
        )

    expected = [
        line
        for line in EXPECTED_APPROVED
        if "draft" not in line  # declined tickets never reach draft_reply
    ]
    assert dump_spans(exporter.get_finished_spans()) == expected


async def test_openinference_enrichment(
    client: Client, reset_otel_tracer_provider: Any
) -> None:
    exporter = _install_in_memory_exporter()
    new_client = _client_with_plugin(client)
    task_queue = f"tq-{uuid.uuid4()}"
    workflow_id = f"ticket-triage-test-{uuid.uuid4()}"

    async with Worker(
        new_client,
        task_queue=task_queue,
        workflows=[TicketTriageWorkflow],
        activities=[classify_ticket_mocked, lookup_account_mocked, draft_reply_mocked],
        max_cached_workflows=0,
    ):
        await _run_interaction(new_client, task_queue, workflow_id, approved=True)

    spans = exporter.get_finished_spans()
    temporal_spans = _temporal_spans(spans)
    assert len(temporal_spans) == 11  # 1 client start, 1 client update, 9 worker-side

    # Every Temporal span gets an OpenInference kind, the Workflow Id as the
    # Arize session, and the Temporal identifiers as OpenInference metadata.
    for span in temporal_spans:
        attributes = dict(span.attributes or {})
        assert attributes[SpanAttributes.OPENINFERENCE_SPAN_KIND] == "CHAIN", span.name
        assert attributes[SpanAttributes.SESSION_ID] == workflow_id, span.name
        assert attributes[SpanAttributes.USER_ID] == TEST_USER, span.name
        metadata = json.loads(str(attributes[SpanAttributes.METADATA]))
        assert metadata["temporalWorkflowID"] == workflow_id, span.name

    # One RunActivity span per attempt, each stamped with its attempt number.
    run_activity_spans = [
        s for s in temporal_spans if s.name.startswith("RunActivity:")
    ]
    assert len(run_activity_spans) == 3
    for span in run_activity_spans:
        attributes = dict(span.attributes or {})
        assert attributes[ACTIVITY_ATTEMPT_ATTRIBUTE] == 1
        assert (
            json.loads(str(attributes[SpanAttributes.METADATA]))[
                "temporalActivityAttempt"
            ]
            == 1
        )

    # Baggage set in the starter reaches spans created inside workflow and
    # activity code (through Temporal's trace-context header), so Arize can
    # group and filter LLM spans by session and user too.
    for name in (
        "triage",
        "mock llm classify",
        "mock account lookup",
        "mock llm draft",
    ):
        span = next(s for s in spans if s.name == name)
        attributes = dict(span.attributes or {})
        assert attributes[SpanAttributes.SESSION_ID] == workflow_id, name
        assert attributes[SpanAttributes.USER_ID] == TEST_USER, name
    triage = next(s for s in spans if s.name == "triage")
    assert (
        dict(triage.attributes or {})[SpanAttributes.OPENINFERENCE_SPAN_KIND] == "CHAIN"
    )


async def test_activity_retry_attempts_are_separate_spans(
    client: Client, reset_otel_tracer_provider: Any
) -> None:
    exporter = _install_in_memory_exporter()
    new_client = _client_with_plugin(client)
    task_queue = f"tq-{uuid.uuid4()}"

    async with Worker(
        new_client,
        task_queue=task_queue,
        workflows=[TicketTriageWorkflow],
        activities=[
            classify_ticket_fails_once,
            lookup_account_mocked,
            draft_reply_mocked,
        ],
        max_cached_workflows=0,
    ):
        await _run_interaction(
            new_client, task_queue, f"ticket-triage-test-{uuid.uuid4()}", approved=True
        )

    spans = exporter.get_finished_spans()
    expected = list(EXPECTED_APPROVED)
    # The failed first attempt adds one RunActivity span (with its inner mock
    # span) under the single StartActivity span.
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
