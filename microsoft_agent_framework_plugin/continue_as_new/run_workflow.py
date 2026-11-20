"""Start the chat workflow, send two turns, then end it."""

# @@@SNIPSTART python-microsoft-agent-framework-continue-as-new-run-workflow
import asyncio
import os

from temporalio.client import Client

from microsoft_agent_framework_plugin.continue_as_new.workflow import (
    ChatInput,
    ChatWorkflow,
)


async def main() -> None:
    client = await Client.connect(os.environ.get("TEMPORAL_ADDRESS", "localhost:7233"))

    handle = await client.start_workflow(
        ChatWorkflow.run,
        ChatInput(),
        id="microsoft-agent-framework-chat",
        task_queue="microsoft-agent-framework-chat",
    )

    for prompt in [
        "Hi! What is durable execution?",
        "Give me a one-sentence summary.",
    ]:
        reply = await handle.execute_update(ChatWorkflow.turn, prompt)
        print(f"user: {prompt}")
        print(f"assistant: {reply}\n")

    transcript = await handle.query(ChatWorkflow.transcript)
    print(f"{len(transcript)} messages in the session")

    await handle.signal(ChatWorkflow.end_chat)
    await handle.result()


if __name__ == "__main__":
    asyncio.run(main())
# @@@SNIPEND
