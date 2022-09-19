import asyncio
import dataclasses

import temporalio.converter
from temporalio.client import Client

from custom_converter.worker import (
    GreetingInput,
    GreetingOutput,
    GreetingPayloadConverter,
    GreetingWorkflow,
)


async def main():
    # Connect client
    client = await Client.connect(
        "localhost:7233",
        # Use the default data converter, but change the payload converter.
        # Without this we get:
        #   TypeError: Object of type GreetingInput is not JSON serializable
        data_converter=dataclasses.replace(
            temporalio.converter.default(),
            payload_converter_class=GreetingPayloadConverter,
        ),
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
