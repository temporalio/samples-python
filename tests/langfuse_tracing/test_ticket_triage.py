"""Tests for the ticket triage sample.

These run without Langfuse or an LLM: the LLM activities are mocked (each
opens a custom span to prove trace context propagates into activities) and
spans are captured with an in-memory exporter. The worker runs with the
workflow cache disabled, so every workflow task replays the workflow from the
start of history — asserting the whole span tree with deep equality proves
spans are emitted exactly once despite replay.
"""

import uuid
from typing import Any

import opentelemetry.trace
from opentelemetry import trace
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from temporalio import activity
from temporalio.client import Client
from temporalio.contrib.opentelemetry import OpenTelemetryPlugin, create_tracer_provider
from temporalio.worker import Replayer, Worker

from langfuse_tracing.ticket_triage.activities import (
    AccountInfo,
    ApprovalDecision,
    Classification,
    DraftReplyInput,
    Ticket,
)
from langfuse_tracing.ticket_triage.workflows import TicketTriageWorkflow
from tests.langfuse_tracing.helpers import dump_spans

TICKET = Ticket(
    ticket_id="T-1",
    customer_email="ada@acme.example",
    subject="Charged twice",
    body="Please refund the duplicate charge.",
)


@activity.defn(name="classify_ticket")
async def classify_ticket_mocked(ticket: Ticket) -> Classification:
    with trace.get_tracer(__name__).start_as_current_span("mock llm classify"):
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
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    opentelemetry.trace.set_tracer_provider(provider)
    return exporter


def _client_with_plugin(client: Client) -> Client:
    config = client.config()
    config["plugins"] = [OpenTelemetryPlugin(add_temporal_spans=True)]
    return Client(**config)


async def _run_workflow(client: Client, task_queue: str, approved: bool) -> Any:
    handle = await client.start_workflow(
        TicketTriageWorkflow.run,
        TICKET,
        id=f"ticket-triage-test-{uuid.uuid4()}",
        task_queue=task_queue,
    )
    await handle.execute_update(
        TicketTriageWorkflow.approve,
        ApprovalDecision(approved=approved, reviewer="test-reviewer"),
    )
    await handle.result()
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


async def test_spans_emitted_exactly_once_under_replay_stress(
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
        # Disable the workflow cache: every workflow task replays the workflow
        # from the start of history. Tracing must still emit each span once.
        max_cached_workflows=0,
    ):
        with trace.get_tracer(__name__).start_as_current_span("ticket-triage test"):
            handle = await _run_workflow(new_client, task_queue, approved=True)

    spans = exporter.get_finished_spans()
    assert dump_spans(spans) == EXPECTED_APPROVED
    span_ids = [s.context.span_id for s in spans if s.context]
    assert len(set(span_ids)) == len(span_ids)

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
        with trace.get_tracer(__name__).start_as_current_span("ticket-triage test"):
            await _run_workflow(new_client, task_queue, approved=False)

    expected = [
        line
        for line in EXPECTED_APPROVED
        if "draft" not in line  # declined tickets never reach draft_reply
    ]
    assert dump_spans(exporter.get_finished_spans()) == expected
