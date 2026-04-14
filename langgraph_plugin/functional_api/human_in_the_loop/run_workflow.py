"""Start the human-in-the-loop chatbot workflow (Functional API)."""

import asyncio

from temporalio.client import Client

from langgraph_plugin.functional_api.human_in_the_loop.workflow import (
    ChatbotFunctionalWorkflow,
)


async def main() -> None:
    client = await Client.connect("localhost:7233")

    handle = await client.start_workflow(
        ChatbotFunctionalWorkflow.run,
        "What is the meaning of life?",
        id="chatbot-functional-workflow",
        task_queue="langgraph-chatbot-functional",
    )

    # Poll until the draft is ready for review
    draft = None
    while draft is None:
        await asyncio.sleep(0.5)
        draft = await handle.query(ChatbotFunctionalWorkflow.get_draft)

    print(f"Draft for review: {draft}")

    # Send approval via signal
    await handle.signal(ChatbotFunctionalWorkflow.provide_feedback, "approve")

    result = await handle.result()
    print(f"Final response: {result}")


if __name__ == "__main__":
    asyncio.run(main())
