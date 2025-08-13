import asyncio
import dataclasses

import temporalio.converter
from temporalio.client import Client
from temporalio.envconfig import ClientConfigProfile

from encryption.codec import EncryptionCodec
from encryption.worker import GreetingWorkflow


async def main():
    # Load configuration
    config_dict = ClientConfigProfile.load().to_dict()
    config_dict.setdefault("address", "localhost:7233")
    config = ClientConfigProfile.from_dict(config_dict)

    # Connect client
    client = await Client.connect(
        **config.to_client_connect_config(),
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
