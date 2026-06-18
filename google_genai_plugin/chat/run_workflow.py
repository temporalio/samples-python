"""Start the chat workflow with a multi-turn conversation."""

# @@@SNIPSTART python-google-genai-chat-run-workflow
import asyncio
import os

from temporalio.client import Client

from google_genai_plugin.chat.workflow import ChatWorkflow


async def main() -> None:
    client = await Client.connect(os.environ.get("TEMPORAL_ADDRESS", "localhost:7233"))

    result = await client.execute_workflow(
        ChatWorkflow.run,
        [
            "My favorite color is teal. Remember that.",
            "What is my favorite color?",
        ],
        id="google-genai-chat",
        task_queue="google-genai-chat",
    )

    for turn, reply in enumerate(result, start=1):
        print(f"Turn {turn}: {reply}")


if __name__ == "__main__":
    asyncio.run(main())
# @@@SNIPEND
