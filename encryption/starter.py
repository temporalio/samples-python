import asyncio
import dataclasses

import temporalio.converter
from temporalio.client import Client
from temporalio.envconfig import ClientConfig

from encryption.codec import EncryptionCodec
from encryption.worker import GreetingWorkflow


async def main():
    # Load configuration
    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")
    # Connect client
    client = await Client.connect(
        **config,
        # Use the default converter, but change the codec
        data_converter=dataclasses.replace(
            temporalio.converter.default(), payload_codec=EncryptionCodec()
        ),
    )

    # Run workflow
    result = await client.execute_workflow(
        GreetingWorkflow.run,
        "Temporal",
        id=f"encryption-workflow-id",
        task_queue="encryption-task-queue",
    )
    print(f"Workflow result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
