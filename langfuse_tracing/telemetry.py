"""Shared OpenTelemetry-to-Langfuse wiring for the langfuse_tracing samples.

Langfuse natively ingests OpenTelemetry traces, so no Langfuse SDK is needed:
spans are exported over OTLP/HTTP to Langfuse's ``/api/public/otel`` endpoint,
authenticated with a project's public/secret API key pair.

The tracer provider comes from ``temporalio.contrib.opentelemetry
.create_tracer_provider()``, which is safe to use inside workflow code: span
IDs are generated deterministically from workflow state and span export is
suppressed during replay, so a workflow that replays (worker restart, cache
eviction, host failover) never produces duplicate spans in Langfuse.
"""

import base64
import logging
import os

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from temporalio.contrib.opentelemetry import create_tracer_provider

logger = logging.getLogger(__name__)


def _langfuse_exporter() -> OTLPSpanExporter:
    host = os.environ.get("LANGFUSE_HOST", "http://localhost:3000").rstrip("/")
    public_key = os.environ.get("LANGFUSE_PUBLIC_KEY")
    secret_key = os.environ.get("LANGFUSE_SECRET_KEY")
    if not public_key or not secret_key:
        raise SystemExit(
            "LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY must be set. Copy "
            "langfuse_tracing/.env.example to langfuse_tracing/.env and load it "
            "in this terminal: set -a; source langfuse_tracing/.env; set +a"
        )
    auth = base64.b64encode(f"{public_key}:{secret_key}".encode()).decode()
    return OTLPSpanExporter(
        # Langfuse's OTLP endpoint is HTTP-only (protobuf or JSON); it has no gRPC
        # listener, so this must be the http exporter, not the grpc one.
        endpoint=f"{host}/api/public/otel/v1/traces",
        headers={
            "Authorization": f"Basic {auth}",
            # Documented by Langfuse: opts into real-time ingestion. Without it,
            # ingested traces can take several minutes to appear in the UI.
            "x-langfuse-ingestion-version": "4",
        },
        timeout=10,
    )


def setup_tracing(service_name: str) -> None:
    """Install a replay-safe tracer provider that exports spans to Langfuse.

    Must be called once at process start, before connecting the Temporal
    client, in every process that traces (worker and starter alike).

    Honors ``OTEL_SDK_DISABLED=true`` as a kill-switch: the provider is still
    installed (the Temporal worker requires it) but no exporter is attached.
    """
    provider = create_tracer_provider(
        resource=Resource.create({SERVICE_NAME: service_name})
    )
    if os.environ.get("OTEL_SDK_DISABLED", "").lower() != "true":
        # A short schedule delay so demo spans show up in Langfuse quickly.
        # Buffered spans are also flushed at process exit (the provider
        # registers a shutdown hook), but call force_flush() before reading
        # traces back to avoid racing the batch.
        provider.add_span_processor(
            BatchSpanProcessor(_langfuse_exporter(), schedule_delay_millis=500)
        )
    else:
        logger.info("OTEL_SDK_DISABLED=true - spans will not be exported")
    trace.set_tracer_provider(provider)


def force_flush() -> None:
    """Flush any buffered spans to Langfuse immediately."""
    # The replay-safe provider implements force_flush but the base
    # opentelemetry TracerProvider type does not declare it, hence getattr.
    flush = getattr(trace.get_tracer_provider(), "force_flush", None)
    if callable(flush):
        flush()


def instrument_openai() -> str:
    """Instrument the OpenAI client library once, in the worker process.

    Every OpenAI API call made from an activity then emits a span that nests
    under that activity's span and that Langfuse renders as a GENERATION
    observation with model, token usage, and cost.

    Two OpenTelemetry instrumentation flavors are supported via the
    ``LLM_INSTRUMENTATION`` env var:

    - ``openinference`` (default): OpenInference semantic conventions. Prompt
      and completion content are recorded on span attributes, which Langfuse
      maps to the observation's input/output.
    - ``openai-v2``: the OpenTelemetry GenAI semantic conventions
      (``gen_ai.*``). Content capture additionally requires
      ``OTEL_SEMCONV_STABILITY_OPT_IN=gen_ai_latest_experimental`` and
      ``OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT=span_only``.
    """
    flavor = os.environ.get("LLM_INSTRUMENTATION", "openinference")
    if flavor == "openinference":
        from openinference.instrumentation.openai import OpenAIInstrumentor

        OpenAIInstrumentor().instrument()
    elif flavor == "openai-v2":
        from opentelemetry.instrumentation.openai_v2 import (
            OpenAIInstrumentor as OpenAIV2Instrumentor,
        )

        OpenAIV2Instrumentor().instrument()
    else:
        raise ValueError(
            f"Unknown LLM_INSTRUMENTATION {flavor!r}; use 'openinference' or 'openai-v2'"
        )
    return flavor
