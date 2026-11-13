"""OpenTelemetry wiring shared by the arize_tracing samples.

Phoenix and Arize AX ingest OTLP/HTTP and read the OpenInference semantic
conventions, so no Arize SDK is involved. The tracer provider comes from
``temporalio.contrib.opentelemetry.create_tracer_provider()``: span IDs are
deterministic and export is suppressed during replay, so a workflow that
replays (worker restart, cache eviction) never duplicates spans in Arize.
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
from opentelemetry.sdk.trace import Span, SpanProcessor
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from temporalio import activity
from temporalio.contrib.opentelemetry import create_tracer_provider

logger = logging.getLogger(__name__)

# Instrumentation scope prefix of the spans Temporal's OpenTelemetryPlugin emits.
TEMPORAL_SCOPE_PREFIX = "temporalio.contrib."
# Attribute this sample adds to RunActivity spans (one span per attempt).
ACTIVITY_ATTEMPT_ATTRIBUTE = "temporal.activity.attempt"


def project_name() -> str:
    """The Phoenix / Arize AX project that receives the spans."""
    return (
        os.environ.get("ARIZE_PROJECT_NAME")
        or os.environ.get("PHOENIX_PROJECT_NAME")
        or "temporal-ticket-triage"
    )


def phoenix_request(url: str) -> urllib.request.Request:
    """A Phoenix REST API request."""
    return urllib.request.Request(url, headers=phoenix_headers())


# @@@SNIPSTART python-arize-tracing-exporter
def phoenix_base_url() -> str:
    """Phoenix base URL; the UI, REST API, and OTLP/HTTP collector share it."""
    return os.environ.get("PHOENIX_COLLECTOR_ENDPOINT", "http://localhost:6006").rstrip(
        "/"
    )


def phoenix_headers() -> dict[str, str]:
    """Authorization header for Phoenix when PHOENIX_API_KEY is set."""
    api_key = os.environ.get("PHOENIX_API_KEY")
    return {"Authorization": f"Bearer {api_key}"} if api_key else {}


def _exporter() -> OTLPSpanExporter:
    """OTLP/HTTP exporter: Arize AX when its credentials are set, else Phoenix."""
    space_id = os.environ.get("ARIZE_SPACE_ID")
    api_key = os.environ.get("ARIZE_API_KEY")
    if space_id and api_key:
        # EU region: ARIZE_OTLP_ENDPOINT=https://otlp.eu-west-1a.arize.com/v1/traces
        return OTLPSpanExporter(
            endpoint=os.environ.get(
                "ARIZE_OTLP_ENDPOINT", "https://otlp.arize.com/v1/traces"
            ),
            headers={"space_id": space_id, "api_key": api_key},
            timeout=10,
        )
    base = phoenix_base_url()
    endpoint = base if base.endswith("/v1/traces") else f"{base}/v1/traces"
    return OTLPSpanExporter(endpoint=endpoint, headers=phoenix_headers(), timeout=10)


# @@@SNIPEND


# @@@SNIPSTART python-arize-tracing-enrichment-processor
class OpenInferenceEnrichmentProcessor(SpanProcessor):
    """Make Temporal's spans first-class in Arize.

    When a span from Temporal's ``OpenTelemetryPlugin`` starts: mark it
    ``openinference.span.kind=CHAIN`` (Arize shows UNKNOWN otherwise), copy the
    Temporal identifiers into OpenInference ``metadata``, set ``session.id`` to
    the Workflow Id so one Workflow Execution's traces form one Arize session,
    and record the attempt number on ``RunActivity`` spans. Any span missing
    ``session.id`` / ``user.id`` gets them from OpenTelemetry baggage, which
    Temporal carries in its trace-context header. Only attributes are set, so
    replay stays silent: spans re-created during replay are never exported.
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
                k: v for k, v in attributes.items() if k.startswith("temporal")
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
            if key not in attributes:
                value = baggage.get_baggage(key, parent_context)
                if value is not None:
                    span.set_attribute(key, str(value))


# @@@SNIPEND


# @@@SNIPSTART python-arize-tracing-setup
def setup_tracing(service_name: str) -> None:
    """Install the replay-safe tracer provider that exports to Phoenix or Arize AX.

    Call once per process, before connecting the Temporal client. With
    ``OTEL_SDK_DISABLED=true`` the provider is still installed (the Temporal
    plugin needs it) but nothing is exported.
    """
    provider = create_tracer_provider(
        resource=Resource.create(
            # The project name selects the Phoenix / Arize AX project.
            {
                SERVICE_NAME: service_name,
                ResourceAttributes.PROJECT_NAME: project_name(),
            }
        )
    )
    provider.add_span_processor(OpenInferenceEnrichmentProcessor())
    if os.environ.get("OTEL_SDK_DISABLED", "").lower() == "true":
        logger.info("OTEL_SDK_DISABLED=true: spans will not be exported")
    else:
        # A short delay so demo spans show up quickly; force_flush() before exit.
        provider.add_span_processor(
            BatchSpanProcessor(_exporter(), schedule_delay_millis=500)
        )
    trace.set_tracer_provider(provider)


# @@@SNIPEND


def force_flush() -> None:
    """Flush buffered spans; short-lived processes call this before exiting."""
    flush = getattr(trace.get_tracer_provider(), "force_flush", None)
    if callable(flush):
        flush()


def trace_url(trace_id: str) -> str:
    """Best-effort deep link to a trace in the Phoenix UI."""
    if os.environ.get("ARIZE_SPACE_ID") and os.environ.get("ARIZE_API_KEY"):
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
