#!/usr/bin/env python3
"""Client for custom spans OTEL example.

This demonstrates using custom_span() to create logical groupings in traces
while still benefiting from automatic instrumentation.
"""

import asyncio
import uuid
from datetime import timedelta

from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from temporalio.client import Client
from temporalio.contrib.openai_agents import ModelActivityParameters, OpenAIAgentsPlugin

from openai_agents.otel_tracing.workflows.otel_custom_spans_workflow import (
    OtelCustomSpansWorkflow,
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

    print("Checking weather for multiple cities...\n")

    result = await client.execute_workflow(
        OtelCustomSpansWorkflow.run,
        id=f"otel-custom-spans-workflow-{uuid.uuid4()}",
        task_queue="otel-task-queue",
    )

    print(f"Results:\n{result}\n")
    print("✓ Workflow completed")
    print("\nView traces at:")
    print("  - Grafana Tempo: http://localhost:3000/explore")
    print("  - Jaeger: http://localhost:16686/")
    print("\nExpected spans in trace:")
    print("  - Multi-city weather check (custom_span grouping)")
    print("  - Agent runs for Tokyo, Paris, New York (3 agents)")
    print("  - Model invocations (activities)")
    print("  - Tool calls (get_weather activities)")


if __name__ == "__main__":
    asyncio.run(main())
