import asyncio
from pathlib import Path

from temporalio.client import Client
from temporalio.contrib.opentelemetry import TracingInterceptor
from temporalio.envconfig import ClientConfig

from open_telemetry.worker import GreetingWorkflow, init_runtime_with_telemetry


async def main():
    runtime = init_runtime_with_telemetry()

    # Get repo root - 1 level deep from root


    repo_root = Path(__file__).resolve().parent.parent


    config_file = repo_root / "temporal.toml"


    
    config = ClientConfig.load_client_connect_config(config_file=str(config_file))
    config["target_host"] = "localhost:7233"
    # Use OpenTelemetry interceptor
    config["interceptors"] = [TracingInterceptor()]
    config["runtime"] = runtime
    
    # Connect client
    client = await Client.connect(**config)

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
