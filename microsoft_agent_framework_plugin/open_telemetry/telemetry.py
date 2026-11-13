"""Tracer provider setup shared by the Worker and the starter."""

import os

import opentelemetry.trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from temporalio.contrib.opentelemetry import create_tracer_provider

OTLP_ENDPOINT = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")


def install_tracer_provider(service_name: str) -> None:
    """Export this process's spans over OTLP, including replay-safe Workflow spans.

    ``create_tracer_provider`` returns the provider ``OpenTelemetryPlugin``
    requires: spans started from Workflow code keep their ids across replays
    and are exported once. Agent Framework starts its agent and chat spans from
    Workflow code through this global provider, so they are replay-safe too.
    """
    provider = create_tracer_provider(
        resource=Resource.create({SERVICE_NAME: service_name})
    )
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(OTLP_ENDPOINT)))
    opentelemetry.trace.set_tracer_provider(provider)
