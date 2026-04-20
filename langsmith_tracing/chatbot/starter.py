"""Interactive CLI starter for the chatbot LangSmith sample."""

import asyncio
import readline  # noqa: F401 — enables input() line editing
import sys
import uuid

import langsmith as ls
from langsmith import traceable
from temporalio.client import Client
from temporalio.contrib.langsmith import LangSmithPlugin
from temporalio.contrib.pydantic import pydantic_data_converter
from temporalio.envconfig import ClientConfig

from langsmith_tracing.chatbot.workflows import ChatbotWorkflow


async def main():
    add_temporal_runs = "--add-temporal-runs" in sys.argv

    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")

    plugin = LangSmithPlugin(
        project_name="langsmith-chatbot",
        add_temporal_runs=add_temporal_runs,
    )

    client = await Client.connect(
        **config,
        data_converter=pydantic_data_converter,
        plugins=[plugin],
    )

    wf_id = f"langsmith-chatbot-{uuid.uuid4().hex[:8]}"

    # Client-side trace wraps the full interactive session. Each turn
    # (signal + query poll) nests under this root span in LangSmith.
    @traceable(
        name=f"Chatbot Session {wf_id[-8:]}",
        run_type="chain",
        tags=["client-side", "chatbot"],
    )
    async def run_session():
        wf_handle = await client.start_workflow(
            ChatbotWorkflow.run,
            id=wf_id,
            task_queue="langsmith-chatbot-task-queue",
        )
        print(f"Started workflow: {wf_handle.id}")
        print('Type a message, "notes" to see saved notes, or "exit" to quit.\n')

        while True:
            user_input = input("You: ").strip()
            if not user_input:
                continue

            if user_input.lower() == "exit":
                await wf_handle.signal(ChatbotWorkflow.exit)
                result = await wf_handle.result()
                print(f"\nWorkflow finished: {result}")
                return

            if user_input.lower() == "notes":
                notes = await wf_handle.query(ChatbotWorkflow.notes)
                if notes:
                    for name, content in notes.items():
                        print(f"  [{name}]: {content}")
                else:
                    print("  (no notes yet)")
                continue

            # Each turn gets its own trace span
            @traceable(
                name=f"Turn: {user_input[:40]}",
                run_type="chain",
                tags=["client-turn"],
            )
            async def send_and_wait(msg: str):
                prev_response = await wf_handle.query(ChatbotWorkflow.last_response)
                await wf_handle.signal(ChatbotWorkflow.user_message, msg)
                for _ in range(60):
                    await asyncio.sleep(0.5)
                    response = await wf_handle.query(ChatbotWorkflow.last_response)
                    if response != prev_response:
                        return response
                return None

            response = await send_and_wait(user_input)
            if response:
                print(f"Bot: {response}\n")
            else:
                print("(timed out waiting for response)")

    try:
        await run_session()
    finally:
        ls.flush()


if __name__ == "__main__":
    asyncio.run(main())
