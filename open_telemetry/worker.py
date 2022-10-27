import asyncio
from datetime import timedelta

from opentelemetry import trace

# See note in README about why Thrift
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from temporalio import activity, workflow
from temporalio.bridge import telemetry
from temporalio.client import Client
from temporalio.contrib.opentelemetry import TracingInterceptor
from temporalio.worker import Worker


@workflow.defn
class GreetingWorkflow:
    @workflow.run
    async def run(self, name: str) -> str:
        return await workflow.execute_activity(
            compose_greeting,
            name,
            start_to_close_timeout=timedelta(seconds=10),
        )


@activity.defn
async def compose_greeting(name: str) -> str:
    return f"Hello, {name}!"


interrupt_event = asyncio.Event()


def init_opentelemetry() -> None:
    # Setup global tracer for workflow traces
    provider = TracerProvider(resource=Resource.create({SERVICE_NAME: "my-service"}))
    provider.add_span_processor(BatchSpanProcessor(JaegerExporter()))
    trace.set_tracer_provider(provider)

    # Setup SDK metrics to OTel endpoint
    telemetry.init_telemetry(
        telemetry.TelemetryConfig(
            otel_metrics=telemetry.OtelCollectorConfig(
                url="http://localhost:4317", headers={}
            )
        )
    )


async def main():
    init_opentelemetry()

    # Connect client
    client = await Client.connect(
        "localhost:7233",
        # Use OpenTelemetry interceptor
        interceptors=[TracingInterceptor()],
    )

    # Run a worker for the workflow
    async with Worker(
        client,
        task_queue="open_telemetry-task-queue",
        workflows=[GreetingWorkflow],
        activities=[compose_greeting],
    ):
        # Wait until interrupted
        print("Worker started, ctrl+c to exit")
        await interrupt_event.wait()
        print("Shutting down")


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        interrupt_event.set()
        loop.run_until_complete(loop.shutdown_asyncgens())
