#!/usr/bin/env python3
"""Client for direct OTEL API usage example.

This demonstrates using the OpenTelemetry API directly in workflows to
instrument custom business logic, add domain-specific spans, and set
custom attributes.

The workflow uses custom_span() to establish OTEL context, then creates
custom spans for validation, business logic, and formatting operations.
"""

import asyncio
import uuid
from datetime import timedelta

from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from temporalio.client import Client
from temporalio.contrib.openai_agents import ModelActivityParameters, OpenAIAgentsPlugin

from openai_agents.otel_tracing.workflows.otel_direct_api_workflow import (
    OtelDirectApiWorkflow,
)


async def main():
    # Configure OTLP exporter (same as worker)
    exporter = OTLPSpanExporter(endpoint="http://localhost:4317", insecure=True)

    client = await Client.connect(
        "localhost:7233",
        plugins=[
            OpenAIAgentsPlugin(
                model_params=ModelActivityParameters(
                    start_to_close_timeout=timedelta(seconds=60)
                ),
                otel_exporters=[exporter],
                add_temporal_spans=False,
            ),
        ],
    )

    city = "Paris"
    print(f"Getting travel recommendation for: {city}\n")

    result = await client.execute_workflow(
        OtelDirectApiWorkflow.run,
        city,
        id=f"otel-direct-api-workflow-{uuid.uuid4()}",
        task_queue="otel-task-queue",
    )

    print(f"Result:\n{result}\n")
    print("✓ Workflow completed")
    print("\nView traces at:")
    print("  - Grafana Tempo: http://localhost:3000/explore")
    print("  - Jaeger: http://localhost:16686/")
    print("\nExpected spans in trace:")
    print("  - Travel recommendation workflow (custom_span)")
    print("  - validate-input (direct OTEL span)")
    print("  - Agent run (Travel Weather Assistant)")
    print("  - fetch-weather-info (direct OTEL span)")
    print("  - Model invocation (activity)")
    print("  - Tool call (get_weather activity)")
    print("  - calculate-travel-score (direct OTEL span)")
    print("  - format-response (direct OTEL span)")
    print("\nLook for custom attributes on spans:")
    print("  - input.city, validation.result")
    print("  - request.city, response.length")
    print("  - travel.score, travel.recommendation")


if __name__ == "__main__":
    asyncio.run(main())
