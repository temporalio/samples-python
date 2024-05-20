import asyncio
from temporalio.client import Client
from workflows import SignalQueryBedrockWorkflow


async def main():
    # brew install temporal
    # temporal server start-dev
    client = await Client.connect("localhost:7233")

    workflow_id = "simple-bedrock-workflow-1"

    handle = client.get_workflow_handle(workflow_id=workflow_id)

    # queries the workflow for the conversation history
    history = await handle.query(
        SignalQueryBedrockWorkflow.get_conversation_history
    )

    print("Conversation History")
    print(
        *(f"{speaker.title()}: {message}\n" for speaker, message in history),
        sep="\n"
    )


if __name__ == "__main__":
    asyncio.run(main())
