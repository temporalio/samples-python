import asyncio
import sys

from temporalio.client import Client
from workflows import EntityBedrockWorkflow


async def main(prompt):
    client = await Client.connect("localhost:7233")

    workflow_id = "entity-bedrock-workflow"

    handle = client.get_workflow_handle(workflow_id)

    # sends a signal to the workflow (and starts it if needed)
    await handle.signal(EntityBedrockWorkflow.end_chat)


if __name__ == "__main__":
    print("Sending signal to end chat.")
    asyncio.run(main(sys.argv))
