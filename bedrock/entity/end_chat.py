import asyncio
import sys

from temporalio.client import Client
from temporalio.envconfig import ClientConfigProfile
from workflows import EntityBedrockWorkflow


async def main():
    # Create client connected to server at the given address
    config_dict = ClientConfigProfile.load().to_dict()
    config_dict.setdefault("address", "localhost:7233")
    config = ClientConfigProfile.from_dict(config_dict)
    client = await Client.connect(**config.to_client_connect_config())

    workflow_id = "entity-bedrock-workflow"

    handle = client.get_workflow_handle_for(EntityBedrockWorkflow.run, workflow_id)

    # Sends a signal to the workflow
    await handle.signal(EntityBedrockWorkflow.end_chat)


if __name__ == "__main__":
    print("Sending signal to end chat.")
    asyncio.run(main())
