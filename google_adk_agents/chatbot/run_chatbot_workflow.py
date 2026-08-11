import asyncio
import os

from temporalio.client import Client
from temporalio.contrib.google_adk_agents import GoogleAdkPlugin

from google_adk_agents.chatbot.workflows.chatbot_workflow import (
    ChatbotAgentWorkflow,
)


async def main():
    # @@@SNIPSTART google-adk-agents-chatbot-starter
    client = await Client.connect(
        os.environ.get("TEMPORAL_ADDRESS", "localhost:7233"),
        plugins=[GoogleAdkPlugin()],
    )

    handle = await client.start_workflow(
        ChatbotAgentWorkflow.run,
        id="google-adk-agents-chatbot-workflow-id",
        task_queue="google-adk-agents-chatbot",
    )

    print('Chat with the assistant. Enter an empty line or "/quit" to exit.')
    while True:
        message = input("> ").strip()
        if not message or message == "/quit":
            break
        reply = await handle.execute_update(ChatbotAgentWorkflow.message, message)
        print(f"Assistant: {reply}")

    await handle.terminate()
    # @@@SNIPEND


if __name__ == "__main__":
    asyncio.run(main())
