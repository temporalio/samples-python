"""Interactive CLI starter for the chatbot LangSmith sample."""

import asyncio
import readline  # noqa: F401 — enables input() line editing
import uuid

import langsmith as ls
from temporalio.client import Client
from temporalio.contrib.langsmith import LangSmithPlugin
from temporalio.contrib.pydantic import pydantic_data_converter
from temporalio.envconfig import ClientConfig

from langsmith_tracing.chatbot.workflows import ChatbotWorkflow


async def main():
    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")

    plugin = LangSmithPlugin(project_name="langsmith-chatbot")

    client = await Client.connect(
        **config,
        data_converter=pydantic_data_converter,
        plugins=[plugin],
    )

    wf_handle = await client.start_workflow(
        ChatbotWorkflow.run,
        id=f"langsmith-chatbot-{uuid.uuid4().hex[:8]}",
        task_queue="langsmith-chatbot-task-queue",
    )
    print(f"Started workflow: {wf_handle.id}")
    print('Type a message, "notes" to see saved notes, or "exit" to quit.\n')

    try:
        while True:
            user_input = input("You: ").strip()
            if not user_input:
                continue

            if user_input.lower() == "exit":
                await wf_handle.signal(ChatbotWorkflow.exit)
                result = await wf_handle.result()
                print(f"\nWorkflow finished: {result}")
                break

            if user_input.lower() == "notes":
                notes = await wf_handle.query(ChatbotWorkflow.notes)
                if notes:
                    for name, content in notes.items():
                        print(f"  [{name}]: {content}")
                else:
                    print("  (no notes yet)")
                continue

            prev_response = await wf_handle.query(ChatbotWorkflow.last_response)
            await wf_handle.signal(ChatbotWorkflow.user_message, user_input)

            # Poll for a new response
            for _ in range(60):
                await asyncio.sleep(0.5)
                response = await wf_handle.query(ChatbotWorkflow.last_response)
                if response != prev_response:
                    print(f"Bot: {response}\n")
                    break
            else:
                print("(timed out waiting for response)")
    finally:
        ls.flush()


if __name__ == "__main__":
    asyncio.run(main())
