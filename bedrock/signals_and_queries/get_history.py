import asyncio

from temporalio.client import Client
from workflows import SignalQueryBedrockWorkflow


async def main():
    # Create client connected to server at the given address
    client = await Client.connect("localhost:7233")
    workflow_id = "bedrock-workflow-with-signals"

    handle = client.get_workflow_handle(workflow_id)

    # Queries the workflow for the conversation history
    history = await handle.query(SignalQueryBedrockWorkflow.get_conversation_history)

    print("Conversation History")
    print(
        *(f"{speaker.title()}: {message}\n" for speaker, message in history), sep="\n"
    )

    # Queries the workflow for the conversation summary
    summary = await handle.query(SignalQueryBedrockWorkflow.get_summary_from_history)

    if summary is not None:
        print("Conversation Summary:")
        print(summary)


if __name__ == "__main__":
    asyncio.run(main())
