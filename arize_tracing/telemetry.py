"""Shared OpenTelemetry wiring for the arize_tracing samples.

Arize Phoenix and Arize AX ingest OpenTelemetry traces over OTLP/HTTP and read
the OpenInference semantic conventions (``openinference.span.kind``,
``session.id``, ``input.value``, ``llm.*`` ...) to render LLM traces, so no
Arize SDK is needed. The same code targets both: Phoenix by default, Arize AX
when ``ARIZE_SPACE_ID`` and ``ARIZE_API_KEY`` are set.

The tracer provider comes from ``temporalio.contrib.opentelemetry
.create_tracer_provider()``, which is safe to use inside workflow code: span
IDs are generated deterministically from workflow state and span export is
suppressed during replay, so a workflow that replays (worker restart, cache
eviction, host failover) never produces duplicate spans in Arize.
"""

import json
import logging
import os
import urllib.request
from typing import Any, Optional

from openinference.semconv.resource import ResourceAttributes
from openinference.semconv.trace import OpenInferenceSpanKindValues, SpanAttributes
from opentelemetry import baggage, trace
from opentelemetry.context import Context
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import ReadableSpan, Span, SpanProcessor
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from temporalio import activity
from temporalio.contrib.opentelemetry import create_tracer_provider

logger = logging.getLogger(__name__)

DEFAULT_PHOENIX_ENDPOINT = "http://localhost:6006"
DEFAULT_ARIZE_ENDPOINT = "https://otlp.arize.com/v1/traces"
DEFAULT_PROJECT_NAME = "temporal-ticket-triage"

# Instrumentation scope prefix of the spans emitted by Temporal's
# OpenTelemetryPlugin (``temporalio.contrib.opentelemetry._otel_interceptor``).
TEMPORAL_SCOPE_PREFIX = "temporalio.contrib."

# Attribute this sample adds to RunActivity spans (one span per attempt).
ACTIVITY_ATTEMPT_ATTRIBUTE = "temporal.activity.attempt"


def project_name() -> str:
    """The Phoenix / Arize AX project that receives the spans."""
    return (
        os.environ.get("ARIZE_PROJECT_NAME")
        or os.environ.get("PHOENIX_PROJECT_NAME")
        or DEFAULT_PROJECT_NAME
    )


def phoenix_base_url() -> str:
    """Phoenix base URL (UI, REST API, and OTLP/HTTP collector share it)."""
    return os.environ.get(
        "PHOENIX_COLLECTOR_ENDPOINT", DEFAULT_PHOENIX_ENDPOINT
    ).rstrip("/")


def exporting_to_arize_ax() -> bool:
    return bool(os.environ.get("ARIZE_SPACE_ID") and os.environ.get("ARIZE_API_KEY"))


# @@@SNIPSTART python-arize-tracing-exporter
def _exporter() -> OTLPSpanExporter:
    """OTLP/HTTP exporter for Arize AX or, by default, Phoenix."""
    space_id = os.environ.get("ARIZE_SPACE_ID")
    api_key = os.environ.get("ARIZE_API_KEY")
    if space_id and api_key:
        # Arize AX (SaaS). For the EU region set
        # ARIZE_OTLP_ENDPOINT=https://otlp.eu-west-1a.arize.com/v1/traces
        return OTLPSpanExporter(
            endpoint=os.environ.get("ARIZE_OTLP_ENDPOINT", DEFAULT_ARIZE_ENDPOINT),
            headers={"space_id": space_id, "api_key": api_key},
            timeout=10,
        )
    # Phoenix (self-hosted or Phoenix Cloud). PHOENIX_COLLECTOR_ENDPOINT is the
    # base URL, as in Phoenix's own tooling; OTLP/HTTP traces go to /v1/traces.
    base = phoenix_base_url()
    endpoint = base if base.endswith("/v1/traces") else f"{base}/v1/traces"
    headers: dict[str, str] = {}
    phoenix_api_key = os.environ.get("PHOENIX_API_KEY")
    if phoenix_api_key:
        headers["Authorization"] = f"Bearer {phoenix_api_key}"
    return OTLPSpanExporter(endpoint=endpoint, headers=headers, timeout=10)


# @@@SNIPEND


# @@@SNIPSTART python-arize-tracing-enrichment-processor
class OpenInferenceEnrichmentProcessor(SpanProcessor):
    """Make Temporal's spans first-class citizens in Arize.

    Temporal's ``OpenTelemetryPlugin`` emits plain spans (``RunWorkflow:*``,
    ``RunActivity:*``, ...). When such a span starts, this processor:

    - marks it ``openinference.span.kind=CHAIN`` so Phoenix and Arize AX stop
      showing it as UNKNOWN,
    - copies the Temporal identifiers into OpenInference ``metadata`` and sets
      ``session.id`` to the Workflow Id, so every trace of a Workflow Execution
      lands in one Arize session,
    - records the attempt number on ``RunActivity:*`` spans (the SDK emits one
      span per attempt but no attempt attribute).

    It also copies ``session.id`` / ``user.id`` from OpenTelemetry baggage onto
    any span that lacks them. The starter sets that baggage; Temporal carries it
    across the client/workflow/activity boundaries in its trace-context header.

    The processor only sets attributes, so it is replay-neutral: spans that are
    re-created during replay are never ended and therefore never exported.
    """

    def on_start(self, span: Span, parent_context: Optional[Context] = None) -> None:
        attributes = dict(span.attributes or {})
        scope = span.instrumentation_scope.name if span.instrumentation_scope else ""
        if scope.startswith(TEMPORAL_SCOPE_PREFIX):
            span.set_attribute(
                SpanAttributes.OPENINFERENCE_SPAN_KIND,
                OpenInferenceSpanKindValues.CHAIN.value,
            )
            metadata: dict[str, Any] = {
                key: value
                for key, value in attributes.items()
                if key.startswith("temporal")
            }
            if activity.in_activity():
                attempt = activity.info().attempt
                span.set_attribute(ACTIVITY_ATTEMPT_ATTRIBUTE, attempt)
                metadata["temporalActivityAttempt"] = attempt
            if metadata:
                span.set_attribute(
                    SpanAttributes.METADATA,
                    json.dumps(metadata, sort_keys=True, default=str),
                )
            workflow_id = attributes.get("temporalWorkflowID")
            if workflow_id and SpanAttributes.SESSION_ID not in attributes:
                span.set_attribute(SpanAttributes.SESSION_ID, str(workflow_id))
                attributes[SpanAttributes.SESSION_ID] = workflow_id
        for key in (SpanAttributes.SESSION_ID, SpanAttributes.USER_ID):
            if key in attributes:
                continue
            value = baggage.get_baggage(key, parent_context)
            if value is not None:
                span.set_attribute(key, str(value))

    def on_end(self, span: ReadableSpan) -> None:
        pass

    def shutdown(self) -> None:
        pass

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        return True


# @@@SNIPEND


# @@@SNIPSTART python-arize-tracing-setup
def setup_tracing(service_name: str) -> None:
    """Install a replay-safe tracer provider that exports spans to Arize.

    Must be called once at process start, before connecting the Temporal
    client, in every process that traces (worker and starter alike).

    Honors ``OTEL_SDK_DISABLED=true`` as a kill switch: the provider is still
    installed (the Temporal plugin requires it) but no exporter is attached.
    """
    provider = create_tracer_provider(
        resource=Resource.create(
            {
                SERVICE_NAME: service_name,
                # Selects the Phoenix / Arize AX project that receives the spans.
                ResourceAttributes.PROJECT_NAME: project_name(),
            }
        )
    )
    provider.add_span_processor(OpenInferenceEnrichmentProcessor())
    if os.environ.get("OTEL_SDK_DISABLED", "").lower() != "true":
        # A short schedule delay so demo spans show up in Arize quickly.
        # Buffered spans are also flushed at process exit (the provider
        # registers a shutdown hook), but call force_flush() before reading
        # traces back to avoid racing the batch.
        provider.add_span_processor(
            BatchSpanProcessor(_exporter(), schedule_delay_millis=500)
        )
    else:
        logger.info("OTEL_SDK_DISABLED=true - spans will not be exported")
    trace.set_tracer_provider(provider)


# @@@SNIPEND


class _IgnoreContextDetachErrors(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return not record.getMessage().startswith("Failed to detach context")


def quiet_otel_context_detach_errors() -> None:
    """Silence OpenTelemetry's "Failed to detach context" errors.

    The OpenInference OpenAI Agents processor attaches an OpenTelemetry
    context when an Agents SDK span starts and detaches it when the span ends.
    Temporal runs each workflow task in its own ``contextvars`` context, so for
    agent spans that outlive a workflow task the detach happens in a different
    context and OpenTelemetry logs an error with a traceback. Tracing is
    unaffected (the spans are still correct and exported once), so processes
    that use ``OpenAIAgentsPlugin(use_otel_instrumentation=True)`` call this
    to keep their logs readable.
    """
    logging.getLogger("opentelemetry.context").addFilter(_IgnoreContextDetachErrors())


def force_flush() -> None:
    """Flush any buffered spans to Arize immediately."""
    # The replay-safe provider implements force_flush but the base
    # opentelemetry TracerProvider type does not declare it, hence getattr.
    flush = getattr(trace.get_tracer_provider(), "force_flush", None)
    if callable(flush):
        flush()


def instrument_openai() -> None:
    """Instrument the OpenAI client library once, in the worker process.

    Every OpenAI API call made from an activity then emits an OpenInference LLM
    span (model, token counts, prompt and completion messages) that nests under
    that activity's span.
    """
    from openinference.instrumentation.openai import OpenAIInstrumentor

    OpenAIInstrumentor().instrument()


def phoenix_request(url: str) -> urllib.request.Request:
    """A Phoenix REST API request, with the API key header when configured."""
    headers: dict[str, str] = {}
    api_key = os.environ.get("PHOENIX_API_KEY")
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return urllib.request.Request(url, headers=headers)


def trace_url(trace_id: str) -> str:
    """Best-effort deep link to a trace in the Phoenix UI.

    Phoenix trace URLs need the project's global ID, which the REST API
    returns; falls back to the projects page if the lookup fails.
    """
    if exporting_to_arize_ax():
        return f"https://app.arize.com (project {project_name()!r}, trace {trace_id})"
    base = phoenix_base_url()
    try:
        with urllib.request.urlopen(
            phoenix_request(f"{base}/v1/projects"), timeout=5
        ) as response:
            projects = json.loads(response.read()).get("data") or []
        for project in projects:
            if project.get("name") == project_name():
                return f"{base}/projects/{project['id']}/traces/{trace_id}"
    except (OSError, ValueError):
        pass
    return f"{base}/projects"
