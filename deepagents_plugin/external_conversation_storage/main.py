"""Run a multi-turn agent that supplies its full transcript to the model."""

import asyncio
import uuid

from langchain_core.messages import AIMessage
from temporalio.converter import DataConverter
from temporalio.deepagents import DeepAgentsPlugin
from temporalio.deepagents.testing import mock_model_provider
from temporalio.worker import Worker

from deepagents_plugin.external_conversation_storage.client import connect_client
from deepagents_plugin.external_conversation_storage.workflow import (
    TASK_QUEUE,
    StoredConversationAgent,
    load_conversation_history,
    save_turn,
)


def create_plugin(data_converter: DataConverter) -> DeepAgentsPlugin:
    """Script replies so the sample runs without an LLM provider or API key."""
    return DeepAgentsPlugin(
        data_converter=data_converter,
        model_provider=mock_model_provider(
            [
                AIMessage(content="The project name is Cedar."),
                AIMessage(content="The project is called Cedar and uses Python."),
                AIMessage(content="Cedar uses Python and is due Friday."),
                AIMessage(content="Cedar is a Python project due Friday."),
            ]
        ),
    )


async def main() -> None:
    user_turns = [
        "I am working on a project called Cedar.",
        "The project uses Python.",
        "It is due Friday.",
        "Remind me of the project name, language, and deadline.",
    ]
    async with connect_client(create_plugin) as client:
        async with Worker(
            client,
            task_queue=TASK_QUEUE,
            workflows=[StoredConversationAgent],
            activities=[load_conversation_history, save_turn],
            max_cached_workflows=0,
        ):
            workflow_id = f"deepagents-conversation-{uuid.uuid4()}"
            handle = await client.start_workflow(
                StoredConversationAgent.run,
                id=workflow_id,
                task_queue=TASK_QUEUE,
            )
            for question in user_turns:
                await handle.signal(StoredConversationAgent.submit_turn, question)
            await handle.signal(StoredConversationAgent.finish)
            result = await handle.result()

    print(f"Workflow: {workflow_id}")
    print(f"Turns processed: {result.turns}")
    print(f"First-turn prompt context: {result.first_context_chars:,} characters")
    print(f"Last-turn prompt context: {result.last_context_chars:,} characters")
    print(f"Final answer: {result.last_answer}")
    print(f"Full transcript stored externally: {result.transcript_turns} turns")
    print("Each model call included the complete conversation history.")


if __name__ == "__main__":
    asyncio.run(main())
