"""Start the human-in-the-loop chatbot workflow (Graph API)."""

import asyncio

from temporalio.client import Client

from langgraph_plugin.graph_api.human_in_the_loop.workflow import ChatbotWorkflow


async def main() -> None:
    client = await Client.connect("localhost:7233")

    handle = await client.start_workflow(
        ChatbotWorkflow.run,
        "What is the meaning of life?",
        id="chatbot-workflow",
        task_queue="langgraph-chatbot",
    )

    # Poll until the draft is ready for review.
    # In a real app, a UI would call this query endpoint.
    draft = None
    while draft is None:
        await asyncio.sleep(0.5)
        draft = await handle.query(ChatbotWorkflow.get_draft)

    print(f"Draft for review: {draft}")

    # Send approval via signal (a UI would trigger this)
    await handle.signal(ChatbotWorkflow.provide_feedback, "approve")

    result = await handle.result()
    print(f"Final response: {result}")


if __name__ == "__main__":
    asyncio.run(main())
