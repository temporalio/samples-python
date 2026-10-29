import os

import opentelemetry.trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from temporalio.contrib.opentelemetry import create_tracer_provider

OTLP_ENDPOINT = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")

# Turns on Claude Code's tracing. Set in the Worker's environment, not in
# options.env, which is recorded in Workflow history.
CLAUDE_CODE_TRACING = {
    "CLAUDE_CODE_ENABLE_TELEMETRY": "1",
    "CLAUDE_CODE_ENHANCED_TELEMETRY_BETA": "1",
    "OTEL_TRACES_EXPORTER": "otlp",
    "OTEL_EXPORTER_OTLP_PROTOCOL": "grpc",
    "OTEL_EXPORTER_OTLP_ENDPOINT": OTLP_ENDPOINT,
    "OTEL_SERVICE_NAME": "claude-code",
}


def install_tracer_provider(service_name: str) -> None:
    """Export this process's spans, including replay-safe Workflow spans."""
    provider = create_tracer_provider(
        resource=Resource.create({SERVICE_NAME: service_name})
    )
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(OTLP_ENDPOINT)))
    opentelemetry.trace.set_tracer_provider(provider)
