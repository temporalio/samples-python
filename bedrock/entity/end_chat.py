import asyncio
import sys

from temporalio.client import Client
from temporalio.envconfig import ClientConfig
from workflows import EntityBedrockWorkflow

from util import get_temporal_config_path


async def main():
    # Create client connected to server at the given address
    config = ClientConfig.load_client_connect_config(
        config_file=str(get_temporal_config_path())
    )

    client = await Client.connect(**config)

    workflow_id = "entity-bedrock-workflow"

    handle = client.get_workflow_handle_for(EntityBedrockWorkflow.run, workflow_id)

    # Sends a signal to the workflow
    await handle.signal(EntityBedrockWorkflow.end_chat)


if __name__ == "__main__":
    print("Sending signal to end chat.")
    asyncio.run(main())
