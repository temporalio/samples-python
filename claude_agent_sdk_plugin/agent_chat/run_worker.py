import asyncio
import os
from typing import Any

from temporalio.claude_agent_sdk import ClaudeAgentSDKPlugin
from temporalio.client import Client
from temporalio.worker import Worker

from claude_agent_sdk_plugin.agent_chat.workflow import ChatWorkflow
from claude_agent_sdk_plugin.offline import Answer, offline_api_without_key


def offline_reply(request: dict[str, Any]) -> str:
    earlier = sum(message["role"] == "assistant" for message in request["messages"])
    return f"Offline reply {earlier + 1} in this conversation."


OFFLINE_ANSWERS: dict[str, Answer] = {"": offline_reply}


async def main() -> None:
    client = await Client.connect(os.environ.get("TEMPORAL_ADDRESS", "localhost:7233"))
    with offline_api_without_key(OFFLINE_ANSWERS):
        worker = Worker(
            client,
            task_queue="claude-agent-sdk-agent-chat",
            workflows=[ChatWorkflow],
            plugins=[ClaudeAgentSDKPlugin()],
        )
        print("Worker started. Ctrl+C to exit.")
        await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
