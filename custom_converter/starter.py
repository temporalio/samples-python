import asyncio

from temporalio.client import Client
from temporalio.envconfig import ClientConfigProfile

from custom_converter.shared import (
    GreetingInput,
    GreetingOutput,
    greeting_data_converter,
)
from custom_converter.workflow import GreetingWorkflow


async def main():
    config = ClientConfigProfile.load()
    config["address"] = "localhost:7233"

    # Connect client
    client = await Client.connect(
        **config.to_client_connect_config(),
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
