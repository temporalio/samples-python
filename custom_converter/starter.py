import asyncio
from pathlib import Path

from temporalio.client import Client
from temporalio.envconfig import ClientConfig

from custom_converter.shared import (
    GreetingInput,
    GreetingOutput,
    greeting_data_converter,
)
from custom_converter.workflow import GreetingWorkflow


async def main():
    # Get repo root - 1 level deep from root

    repo_root = Path(__file__).resolve().parent.parent

    config_file = repo_root / "temporal.toml"

    
    config = ClientConfig.load_client_connect_config(config_file=str(config_file))
    config["target_host"] = "localhost:7233"
    # Without this we get:
    #   TypeError: Object of type GreetingInput is not JSON serializable
    config["data_converter"] = greeting_data_converter
    
    # Connect client
    client = await Client.connect(**config)

    # Run workflow
    result = await client.execute_workflow(
        GreetingWorkflow.run,
        GreetingInput("Temporal"),
        id=f"custom_converter-workflow-id",
        task_queue="custom_converter-task-queue",
    )
    assert isinstance(result, GreetingOutput)
    print(f"Workflow result: {result.result}")


if __name__ == "__main__":
    asyncio.run(main())
