#!/usr/bin/env python3
"""Client for basic OTEL tracing example.

This demonstrates the simplest OTEL integration - automatic instrumentation
of agent/model/activity spans without any custom code.

The worker configuration handles all OTEL setup. This client just executes
the workflow normally.
"""

import asyncio
import uuid
from datetime import timedelta

from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from temporalio.client import Client
from temporalio.contrib.openai_agents import ModelActivityParameters, OpenAIAgentsPlugin

from openai_agents.otel_tracing.workflows.otel_basic_workflow import OtelBasicWorkflow


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

    question = "What's the weather like in Tokyo?"
    print(f"Question: {question}\n")

    result = await client.execute_workflow(
        OtelBasicWorkflow.run,
        question,
        id=f"otel-basic-workflow-{uuid.uuid4()}",
        task_queue="otel-task-queue",
    )

    print(f"Answer: {result}\n")
    print("✓ Workflow completed")
    print("\nView traces at:")
    print("  - Grafana Tempo: http://localhost:3000/explore")
    print("  - Jaeger: http://localhost:16686/")
    print("\nExpected spans in trace:")
    print("  - Agent run (Weather Assistant)")
    print("  - Model invocation (activity)")
    print("  - Tool call (get_weather activity)")


if __name__ == "__main__":
    asyncio.run(main())
