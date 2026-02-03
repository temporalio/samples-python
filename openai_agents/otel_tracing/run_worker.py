#!/usr/bin/env python3
"""Worker for OTEL tracing examples.

This worker demonstrates OTEL configuration for both automatic instrumentation
and direct OTEL API usage patterns.

Configuration:
- OTLP exporter for sending traces to OTEL backend
- Sandbox passthrough for opentelemetry module (required for direct API usage)
- Optional add_temporal_spans parameter for controlling span verbosity
"""

import asyncio
from datetime import timedelta

from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from temporalio.client import Client
from temporalio.contrib.openai_agents import ModelActivityParameters, OpenAIAgentsPlugin
from temporalio.worker import Worker
from temporalio.worker.workflow_sandbox import (
    SandboxedWorkflowRunner,
    SandboxRestrictions,
)

from openai_agents.otel_tracing.workflows.otel_basic_workflow import (
    OtelBasicWorkflow,
    get_weather,
)
from openai_agents.otel_tracing.workflows.otel_custom_spans_workflow import (
    OtelCustomSpansWorkflow,
)
from openai_agents.otel_tracing.workflows.otel_direct_api_workflow import (
    OtelDirectApiWorkflow,
)


async def main():
    # Configure OTLP exporter
    # Default endpoint is localhost:4317 for Grafana Tempo/Jaeger
    # Adjust endpoint for your OTEL backend (e.g., Datadog, New Relic, etc.)
    exporter = OTLPSpanExporter(endpoint="http://localhost:4317", insecure=True)

    client = await Client.connect(
        "localhost:7233",
        plugins=[
            OpenAIAgentsPlugin(
                model_params=ModelActivityParameters(
                    start_to_close_timeout=timedelta(seconds=60)
                ),
                otel_exporters=[exporter],
                # Optional: Set to False to exclude Temporal internal spans for cleaner traces
                add_temporal_spans=False,
            ),
        ],
    )

    worker = Worker(
        client,
        task_queue="otel-task-queue",
        workflows=[OtelBasicWorkflow, OtelCustomSpansWorkflow, OtelDirectApiWorkflow],
        activities=[get_weather],
        # CRITICAL: Sandbox passthrough required for direct OTEL API usage
        # If you only use automatic instrumentation (OtelBasicWorkflow),
        # this configuration is not required
        workflow_runner=SandboxedWorkflowRunner(
            SandboxRestrictions.default.with_passthrough_modules("opentelemetry")
        ),
    )

    print("Starting OTEL tracing worker...")
    print("- Task queue: otel-task-queue")
    print("- OTLP endpoint: http://localhost:4317")
    print(
        "- Workflows: OtelBasicWorkflow, OtelCustomSpansWorkflow, OtelDirectApiWorkflow"
    )
    print("\nConfiguration:")
    print("  - Automatic instrumentation: ENABLED (all workflows)")
    print("  - Custom spans support: ENABLED")
    print("  - Direct OTEL API support: ENABLED (sandbox passthrough configured)")
    print("  - Temporal spans: DISABLED (add_temporal_spans=False)")
    print("\nView traces at: http://localhost:3000/explore (Grafana Tempo)")
    print("              or http://localhost:16686/ (Jaeger)\n")

    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
