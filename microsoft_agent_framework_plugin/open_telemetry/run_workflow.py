"""Start the traced workflow under a root span and print the trace id."""

# @@@SNIPSTART python-microsoft-agent-framework-open-telemetry-run-workflow
import asyncio
import os

import opentelemetry.trace
from temporalio.client import Client
from temporalio.contrib.opentelemetry import OpenTelemetryPlugin

from microsoft_agent_framework_plugin.open_telemetry.telemetry import (
    install_tracer_provider,
)
from microsoft_agent_framework_plugin.open_telemetry.workflow import TracedWorkflow


async def main() -> None:
    install_tracer_provider("microsoft-agent-framework-starter")
    client = await Client.connect(
        os.environ.get("TEMPORAL_ADDRESS", "localhost:7233"),
        plugins=[OpenTelemetryPlugin(add_temporal_spans=True)],
    )

    # The root of the trace. The Workflow, its model Activity and Agent
    # Framework's own spans all join it.
    tracer = opentelemetry.trace.get_tracer(__name__)
    with tracer.start_as_current_span("ask-agent") as span:
        result = await client.execute_workflow(
            TracedWorkflow.run,
            "What is durable execution? Answer in one sentence.",
            id="microsoft-agent-framework-open-telemetry",
            task_queue="microsoft-agent-framework-open-telemetry",
        )
        trace_id = format(span.get_span_context().trace_id, "032x")

    print(f"Result: {result}")
    print(f"Trace ID: {trace_id}")


if __name__ == "__main__":
    asyncio.run(main())
# @@@SNIPEND
