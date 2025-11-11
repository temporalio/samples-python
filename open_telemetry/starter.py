import asyncio

from temporalio.client import Client
from temporalio.contrib.opentelemetry import TracingInterceptor
from temporalio.envconfig import ClientConfig

from open_telemetry.worker import GreetingWorkflow, init_runtime_with_telemetry


async def main():
    runtime = init_runtime_with_telemetry()

    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")
    # Connect client
    client = await Client.connect(
        **config,
        # Use OpenTelemetry interceptor
        interceptors=[TracingInterceptor()],
        runtime=runtime,
    )

    # Run workflow
    result = await client.execute_workflow(
        GreetingWorkflow.run,
        "Temporal",
        id=f"open_telemetry-workflow-id",
        task_queue="open_telemetry-task-queue",
    )
    print(f"Workflow result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
