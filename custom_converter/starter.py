import asyncio

from temporalio.client import Client
from temporalio.envconfig import ClientConfig

from custom_converter.shared import (
    GreetingInput,
    GreetingOutput,
    greeting_data_converter,
)
from custom_converter.workflow import GreetingWorkflow
from util import get_temporal_config_path


async def main():
    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")

    # Connect client
    client = await Client.connect(
        **config,
        # Without this we get:
        #   TypeError: Object of type GreetingInput is not JSON serializable
        data_converter=greeting_data_converter,
    )

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
