import asyncio

from temporalio.client import Client
from temporalio.contrib.opentelemetry import TracingInterceptor
from temporalio.envconfig import ClientConfigProfile

from open_telemetry.worker import GreetingWorkflow, init_runtime_with_telemetry


async def main():
    runtime = init_runtime_with_telemetry()

    config = ClientConfigProfile.load()
    config["address"] = "localhost:7233"

    # Connect client
    client = await Client.connect(
        **config.to_client_connect_config(),
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
