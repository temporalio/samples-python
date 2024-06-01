import asyncio

from temporalio.client import Client
from workflows import EntityBedrockWorkflow


async def main():
    client = await Client.connect("localhost:7233")
    workflow_id = "entity-bedrock-workflow"

    handle = client.get_workflow_handle(workflow_id=workflow_id)

    # queries the workflow for the conversation history
    history = await handle.query(EntityBedrockWorkflow.get_conversation_history)

    print("Conversation History")
    print(
        *(f"{speaker.title()}: {message}\n" for speaker, message in history), sep="\n"
    )

    # queries the workflow for the conversation summary
    summary = await handle.query(EntityBedrockWorkflow.get_summary_from_history)

    print("Conversation Summary:")
    print(summary)


if __name__ == "__main__":
    asyncio.run(main())
