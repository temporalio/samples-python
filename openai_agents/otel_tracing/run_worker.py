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

    worker = Worker(
        client,
        task_queue="otel-task-queue",
        workflows=[OtelBasicWorkflow, OtelCustomSpansWorkflow, OtelDirectApiWorkflow],
        activities=[get_weather],
        workflow_runner=SandboxedWorkflowRunner(
            SandboxRestrictions.default.with_passthrough_modules("opentelemetry")
        ),
    )

    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
