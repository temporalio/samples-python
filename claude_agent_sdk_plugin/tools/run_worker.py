import asyncio
import os

from temporalio.claude_agent_sdk import ClaudeAgentSDKPlugin
from temporalio.client import Client
from temporalio.worker import Worker

from claude_agent_sdk_plugin.offline import (
    Answer,
    offline_api_without_key,
    tool_use,
)
from claude_agent_sdk_plugin.tools.workflow import ToolsWorkflow, fetch_weather

OFFLINE_ANSWERS: dict[str, Answer] = {
    "strawberry": tool_use(
        "toolu_count", "mcp__demo__count_letter", word="strawberry", letter="r"
    ),
    "tool_result:toolu_count": tool_use(
        "toolu_weather", "mcp__demo__get_weather", city="Paris"
    ),
    "tool_result:toolu_weather": (
        "There are 3 r's in strawberry. It is 21 C and sunny in Paris."
    ),
}


async def main() -> None:
    client = await Client.connect(os.environ.get("TEMPORAL_ADDRESS", "localhost:7233"))
    with offline_api_without_key(OFFLINE_ANSWERS):
        worker = Worker(
            client,
            task_queue="claude-agent-sdk-tools",
            workflows=[ToolsWorkflow],
            activities=[fetch_weather],
            plugins=[ClaudeAgentSDKPlugin()],
        )
        print("Worker started. Ctrl+C to exit.")
        await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
