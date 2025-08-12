import asyncio

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

    handle = client.get_workflow_handle(workflow_id)

    # Queries the workflow for the conversation history
    history = await handle.query(EntityBedrockWorkflow.get_conversation_history)

    print("Conversation History")
    print(
        *(f"{speaker.title()}: {message}\n" for speaker, message in history), sep="\n"
    )

    # Queries the workflow for the conversation summary
    summary = await handle.query(EntityBedrockWorkflow.get_summary_from_history)

    if summary is not None:
        print("Conversation Summary:")
        print(summary)


if __name__ == "__main__":
    asyncio.run(main())
