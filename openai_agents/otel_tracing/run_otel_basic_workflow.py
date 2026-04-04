import asyncio
import uuid
from datetime import timedelta

from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from temporalio.client import Client
from temporalio.contrib.openai_agents import ModelActivityParameters, OpenAIAgentsPlugin

from openai_agents.otel_tracing.workflows.otel_basic_workflow import OtelBasicWorkflow


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

    result = await client.execute_workflow(
        OtelBasicWorkflow.run,
        "What's the weather like in Tokyo?",
        id=f"otel-basic-workflow-{uuid.uuid4()}",
        task_queue="otel-task-queue",
    )

    print(f"Result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
