import asyncio
import sys

from temporalio.client import Client
from workflows import EntityBedrockWorkflow


async def main():
    # Create client connected to server at the given address
        # Get repo root - 2 levels deep from root
        repo_root = Path(__file__).resolve().parent.parent.parent
        config_file = repo_root / "temporal.toml"
    config = ClientConfig.load_client_connect_config(config_file=str(config_file))
    config["target_host"] = "localhost:7233"
    client = await Client.connect(**config)

    workflow_id = "entity-bedrock-workflow"

    handle = client.get_workflow_handle_for(EntityBedrockWorkflow.run, workflow_id)

    # Sends a signal to the workflow
    await handle.signal(EntityBedrockWorkflow.end_chat)


if __name__ == "__main__":
    print("Sending signal to end chat.")
    asyncio.run(main())
