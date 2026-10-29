import asyncio
import os
import signal

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

    # Shut the Worker down on SIGTERM, so the plugin stops Claude Code and a
    # restarted Worker can resume its session.
    stop = asyncio.Event()
    asyncio.get_running_loop().add_signal_handler(signal.SIGTERM, stop.set)

    with offline_api_without_key(OFFLINE_ANSWERS):
        async with Worker(
            client,
            task_queue="claude-agent-sdk-tools",
            workflows=[ToolsWorkflow],
            activities=[fetch_weather],
            plugins=[ClaudeAgentSDKPlugin()],
        ):
            print(f"Worker started. To stop it gracefully: kill {os.getpid()}")
            await stop.wait()


if __name__ == "__main__":
    asyncio.run(main())
