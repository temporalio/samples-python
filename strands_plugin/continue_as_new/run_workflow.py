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

    await handle.signal(ChatWorkflow.user_says, "Hi! What is durable execution?")
    await asyncio.sleep(2)
    await handle.signal(ChatWorkflow.user_says, "Give me a one-sentence summary.")
    await asyncio.sleep(2)

    messages = await handle.query(ChatWorkflow.messages)
    print(f"Conversation so far ({len(messages)} messages):")
    for message in messages:
        print(f"  {message['role']}: {message['content']}")

    await handle.signal(ChatWorkflow.end_chat)
    await handle.result()


if __name__ == "__main__":
    asyncio.run(main())
