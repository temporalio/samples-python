import asyncio
import sys

from temporalio.client import Client
from temporalio.envconfig import ClientConfigProfile
from workflows import BedrockParams, EntityBedrockWorkflow


async def main(prompt):
    # Create client connected to server at the given address
    config_dict = ClientConfigProfile.load().to_dict()
    config_dict.setdefault("address", "localhost:7233")
    config = ClientConfigProfile.from_dict(config_dict)
    client = await Client.connect(**config.to_client_connect_config())

    workflow_id = "entity-bedrock-workflow"

    # Sends a signal to the workflow (and starts it if needed)
    await client.start_workflow(
        EntityBedrockWorkflow.run,
        BedrockParams(None, None),
        id=workflow_id,
        task_queue="bedrock-task-queue",
        start_signal="user_prompt",
        start_signal_args=[prompt],
    )


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python send_message.py '<prompt>'")
        print("Example: python send_message.py 'What animals are marsupials?'")
    else:
        asyncio.run(main(sys.argv[1]))
