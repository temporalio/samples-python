"""Start the chat workflow, send a few turns, then end it."""

import asyncio
import os

from temporalio.client import Client
from temporalio.contrib.strands import StrandsPlugin

from strands_plugin.continue_as_new.workflow import ChatInput, ChatWorkflow


async def main() -> None:
    client = await Client.connect(
        os.environ.get("TEMPORAL_ADDRESS", "localhost:7233"),
        plugins=[StrandsPlugin()],
    )

    handle = await client.start_workflow(
        ChatWorkflow.run,
        ChatInput(),
        id="strands-chat",
        task_queue="strands-chat",
    )

    for prompt in [
        "Hi! What is durable execution?",
        "Give me a one-sentence summary.",
    ]:
        reply = await handle.execute_update(ChatWorkflow.turn, prompt)
        print(f"user: {prompt}")
        print(f"assistant: {reply}\n")

    await handle.signal(ChatWorkflow.end_chat)
    await handle.result()


if __name__ == "__main__":
    asyncio.run(main())
