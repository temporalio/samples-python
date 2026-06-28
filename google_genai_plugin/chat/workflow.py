"""Multi-turn chat using client.chats.

A chat session keeps conversation history across turns. Each ``send_message``
call runs as a durable Temporal activity, and the SDK threads prior turns into
each request automatically.
"""

# @@@SNIPSTART python-google-genai-chat-workflow
from temporalio import workflow
from temporalio.contrib.google_genai import TemporalAsyncClient


@workflow.defn
class ChatWorkflow:
    @workflow.run
    async def run(self, prompts: list[str]) -> list[str]:
        client = TemporalAsyncClient()
        chat = client.chats.create(model="gemini-2.5-flash")
        replies: list[str] = []
        for prompt in prompts:
            response = await chat.send_message(prompt)
            replies.append(response.text or "")
        return replies


# @@@SNIPEND
