"""Interactive CLI starter for the chatbot LangSmith sample."""

import asyncio
import readline  # noqa: F401 — enables input() line editing
import sys
import uuid

from langsmith import traceable
from temporalio.client import Client
from temporalio.contrib.langsmith import LangSmithPlugin
from temporalio.contrib.pydantic import pydantic_data_converter
from temporalio.envconfig import ClientConfig

from langsmith_tracing.chatbot.workflows import ChatbotWorkflow

PROJECT_NAME = "langsmith-chatbot"


async def main():
    add_temporal_runs = "--add-temporal-runs" in sys.argv

    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")

    plugin = LangSmithPlugin(
        project_name=PROJECT_NAME,
        add_temporal_runs=add_temporal_runs,
    )

    client = await Client.connect(
        **config,
        data_converter=pydantic_data_converter,
        plugins=[plugin],
    )

    wf_id = f"langsmith-chatbot-{uuid.uuid4().hex[:8]}"

    @traceable(
        name=f"Chatbot Session {wf_id[-8:]}",
        run_type="chain",
        # CRITICAL: Client-side @traceable runs outside the LangSmithPlugin's scope.
        # Make sure client-side traces use the same project_name as what is given to
        # the plugin.
        project_name=PROJECT_NAME,
        tags=["client-side", "chatbot"],
    )
    async def run_session():
        wf_handle = await client.start_workflow(
            ChatbotWorkflow.run,
            id=wf_id,
            task_queue="langsmith-chatbot-task-queue",
        )
        print(f"Started workflow: {wf_handle.id}")
        print('Type a message or "exit" to quit.\n')

        while True:
            user_input = input("> ").strip()
            if not user_input:
                continue

            if user_input.lower() == "exit":
                await wf_handle.signal(ChatbotWorkflow.exit)
                result = await wf_handle.result()
                print(f"\nWorkflow finished: {result}")
                return

            response = await wf_handle.execute_update(
                ChatbotWorkflow.message_from_user, user_input
            )
            print(f"Bot: {response}\n")

    await run_session()


if __name__ == "__main__":
    asyncio.run(main())
