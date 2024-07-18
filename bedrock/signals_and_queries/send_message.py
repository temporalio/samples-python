import asyncio
import sys

from temporalio.client import Client
from workflows import SignalQueryBedrockWorkflow


async def main(prompt):
    # Create client connected to server at the given address
    client = await Client.connect("localhost:7233")

    workflow_id = "bedrock-workflow-with-signals"
    inactivity_timeout_minutes = 1

    # Sends a signal to the workflow (and starts it if needed)
    await client.start_workflow(
        SignalQueryBedrockWorkflow.run,
        inactivity_timeout_minutes,
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
