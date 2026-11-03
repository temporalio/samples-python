import asyncio
import os
import sys

import opentelemetry.trace
from temporalio.client import Client
from temporalio.contrib.opentelemetry import OpenTelemetryPlugin

from claude_agent_sdk_plugin.open_telemetry.telemetry import install_tracer_provider
from claude_agent_sdk_plugin.open_telemetry.workflow import OpenTelemetryWorkflow

DEFAULT_PROMPT = "How many Python files are in the current directory?"


async def main() -> None:
    install_tracer_provider("claude-agent-sdk-starter")
    client = await Client.connect(
        os.environ.get("TEMPORAL_ADDRESS", "localhost:7233"),
        plugins=[OpenTelemetryPlugin(add_temporal_spans=True)],
    )

    # The root of the trace. The Workflow, its Activities, and Claude Code's
    # spans all join it.
    tracer = opentelemetry.trace.get_tracer(__name__)
    with tracer.start_as_current_span("ask-agent") as span:
        result = await client.execute_workflow(
            OpenTelemetryWorkflow.run,
            " ".join(sys.argv[1:]) or DEFAULT_PROMPT,
            id="claude-agent-sdk-open-telemetry",
            task_queue="claude-agent-sdk-open-telemetry",
        )
        trace_id = format(span.get_span_context().trace_id, "032x")

    print(f"Result: {result}")
    print(f"Trace ID: {trace_id}")


if __name__ == "__main__":
    asyncio.run(main())
