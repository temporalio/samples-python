import asyncio
import sys

from temporalio.client import Client
from temporalio.envconfig import ClientConfigProfile
from workflows import EntityBedrockWorkflow


async def main():
    # Create client connected to server at the given address
    config = ClientConfigProfile.load()
    config["address"] = "localhost:7233"
    client = await Client.connect(**config.to_client_connect_config())

    workflow_id = "entity-bedrock-workflow"

    handle = client.get_workflow_handle_for(EntityBedrockWorkflow.run, workflow_id)

    # Sends a signal to the workflow
    await handle.signal(EntityBedrockWorkflow.end_chat)


if __name__ == "__main__":
    print("Sending signal to end chat.")
    asyncio.run(main())
