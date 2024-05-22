import asyncio
import sys
from temporalio.client import Client
from workflows import SimpleBedrockWorkflow


async def main(prompt):
    # brew install temporal
    # temporal server start-dev
    client = await Client.connect("localhost:7233")

    # Start the workflow
    workflow_id = "simple-bedrock-workflow-1"
    await client.start_workflow(
        SimpleBedrockWorkflow.run,
        prompt,  # Initial prompt
        id=workflow_id,
        task_queue="bedrock-task-queue"
    )
    print("Chat started. Workflow ID: {workflow_id}\n")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python send_message.py '<prompt>'")
        print("Example: python send_message.py 'What animals are marsupials?'")
    else:
        asyncio.run(main(sys.argv[1]))