"""Tests for the ticket triage agents sample.

These run without Arize or an LLM: the model is mocked with the SDK's
``TestModel`` (a tool call, then the classification, then the reply), spans are
captured with an in-memory exporter, and the worker runs with the workflow
cache disabled so every workflow task replays the agent loop from history.

Client and worker share one process here, and therefore one OpenInference
processor. The worker-side trace replicas that Temporal creates for context
propagation register under the same trace id as the client's trace, so in a
single process the client's root span is not the span that ends when the
Agents SDK trace ends. The sample runs starter and worker as separate
processes, where the root exports correctly; these assertions therefore focus
on the worker-side tree.
"""

import json
import uuid
from datetime import timedelta
from typing import Any, Optional, Sequence

import opentelemetry.trace
from agents import trace as agents_trace
from openinference.semconv.trace import SpanAttributes
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from temporalio.client import Client
from temporalio.contrib.openai_agents import ModelActivityParameters
from temporalio.contrib.openai_agents.testing import (
    AgentEnvironment,
    ResponseBuilders,
    TestModel,
)
from temporalio.contrib.opentelemetry import create_tracer_provider
from temporalio.worker import Replayer, Worker

from arize_tracing.telemetry import (
    OpenInferenceEnrichmentProcessor,
    quiet_otel_context_detach_errors,
)
from arize_tracing.ticket_triage.activities import (
    ApprovalDecision,
    Ticket,
    lookup_account,
)
from arize_tracing.ticket_triage_agents.workflows import (
    AgentTicketRequest,
    TicketTriageAgentsWorkflow,
)

TICKET = Ticket(
    ticket_id="T-1",
    customer_email="ada@acme.example",
    subject="Charged twice",
    body="Please refund the duplicate charge.",
)


def _model_responses() -> list[Any]:
    return [
        ResponseBuilders.tool_call(
            json.dumps({"customer_email": TICKET.customer_email}), "lookup_account"
        ),
        ResponseBuilders.output_message('{"category": "billing", "priority": "high"}'),
        ResponseBuilders.output_message("Sorry about that - refund on the way."),
    ]


def _install_in_memory_exporter() -> InMemorySpanExporter:
    exporter = InMemorySpanExporter()
    provider = create_tracer_provider()
    provider.add_span_processor(OpenInferenceEnrichmentProcessor())
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    opentelemetry.trace.set_tracer_provider(provider)
    return exporter


def _kind(span: ReadableSpan) -> str:
    return str(dict(span.attributes or {}).get(SpanAttributes.OPENINFERENCE_SPAN_KIND))


def _ancestors(span: ReadableSpan, spans: Sequence[ReadableSpan]) -> list[str]:
    by_id = {s.context.span_id: s for s in spans if s.context}
    names: list[str] = []
    parent: Optional[Any] = span.parent
    while parent is not None and parent.span_id in by_id:
        current = by_id[parent.span_id]
        names.append(current.name)
        parent = current.parent
    return names


def _only(spans: Sequence[ReadableSpan], name: str) -> ReadableSpan:
    matches = [s for s in spans if s.name == name]
    assert len(matches) == 1, f"expected one {name!r} span, found {len(matches)}"
    return matches[0]


async def test_agent_spans_emitted_exactly_once_under_replay_stress(
    client: Client, reset_otel_tracer_provider: Any
) -> None:
    quiet_otel_context_detach_errors()
    # The provider must exist before the plugin is constructed.
    exporter = _install_in_memory_exporter()
    workflow_id = f"ticket-triage-agents-test-{uuid.uuid4()}"
    task_queue = f"tq-{uuid.uuid4()}"

    async with AgentEnvironment(
        model=TestModel.returning_responses(_model_responses()),
        use_otel_instrumentation=True,
        add_temporal_spans=True,
        model_params=ModelActivityParameters(
            start_to_close_timeout=timedelta(seconds=30)
        ),
    ) as env:
        new_client = env.applied_on_client(client)
        async with Worker(
            new_client,
            task_queue=task_queue,
            workflows=[TicketTriageAgentsWorkflow],
            activities=[lookup_account],
            max_cached_workflows=0,
        ):
            with env.openai_agents_plugin.tracing_context():
                with agents_trace("Ticket triage agents test", group_id=workflow_id):
                    handle = await new_client.start_workflow(
                        TicketTriageAgentsWorkflow.run,
                        AgentTicketRequest(ticket=TICKET, model="test-model"),
                        id=workflow_id,
                        task_queue=task_queue,
                    )
                    await handle.execute_update(
                        TicketTriageAgentsWorkflow.approve,
                        ApprovalDecision(approved=True, reviewer="test-reviewer"),
                    )
                    result = await handle.result()

    assert result.status == "replied"
    assert result.classification.category == "billing"

    spans = exporter.get_finished_spans()

    # Every span has an OpenInference kind, so nothing renders as UNKNOWN.
    kinds: dict[str, set[str]] = {}
    for span in spans:
        kinds.setdefault(_kind(span), set()).add(span.name)
    assert "None" not in kinds and "UNKNOWN" not in kinds
    assert {"Triage agent", "Reply agent"} <= kinds["AGENT"]
    assert "lookup_account" in kinds["TOOL"]
    assert {
        "temporal:startWorkflow:TicketTriageAgentsWorkflow",
        "temporal:executeWorkflow",
        "temporal:startActivity",
        "temporal:executeActivity",
        "temporal:updateWorkflow",
    } <= kinds["CHAIN"]

    # Exactly once, in one trace, despite the workflow cache being disabled.
    span_ids = [s.context.span_id for s in spans if s.context]
    assert len(set(span_ids)) == len(span_ids)
    assert len({s.context.trace_id for s in spans if s.context}) == 1

    # Worker-side tree: the agents nest under the workflow execution, and the
    # tool call wraps the activity that implements it.
    execute = _only(spans, "temporal:executeWorkflow")
    assert _ancestors(execute, spans)[:1] == [
        "temporal:startWorkflow:TicketTriageAgentsWorkflow"
    ]
    for agent in ("Triage agent", "Reply agent"):
        assert "temporal:executeWorkflow" in _ancestors(_only(spans, agent), spans)
    tool = _only(spans, "lookup_account")
    assert "Triage agent" in _ancestors(tool, spans)
    tool_activity_starts = [
        s
        for s in spans
        if s.name == "temporal:startActivity"
        and s.parent
        and tool.context
        and s.parent.span_id == tool.context.span_id
    ]
    assert len(tool_activity_starts) == 1

    # Replaying the finished workflow's real history must emit zero new spans.
    history = await handle.fetch_history()
    before = len(exporter.get_finished_spans())
    replayer = Replayer(
        workflows=[TicketTriageAgentsWorkflow], plugins=[env.openai_agents_plugin]
    )
    await replayer.replay_workflow(history)
    assert len(exporter.get_finished_spans()) == before
