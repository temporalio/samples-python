import asyncio
import sys

from temporalio.client import Client
from temporalio.envconfig import ClientConfigProfile
from workflows import BasicBedrockWorkflow


async def main(prompt: str) -> str:
    # Create client connected to server at the given address
    config = ClientConfigProfile.load()
    config["address"] = "localhost:7233"
    client = await Client.connect(**config.to_client_connect_config())

    # Start the workflow
    workflow_id = "basic-bedrock-workflow"
    handle = await client.start_workflow(
        BasicBedrockWorkflow.run,
        prompt,  # Initial prompt
        id=workflow_id,
        task_queue="bedrock-task-queue",
    )
    return await handle.result()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python send_message.py '<prompt>'")
        print("Example: python send_message.py 'What animals are marsupials?'")
    else:
        result = asyncio.run(main(sys.argv[1]))
        print(result)
