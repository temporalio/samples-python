import asyncio
import os
import signal
from typing import Any

from temporalio.claude_agent_sdk import ClaudeAgentSDKPlugin
from temporalio.client import Client
from temporalio.worker import Worker

from claude_agent_sdk_plugin.human_in_the_loop.workflow import HumanInTheLoopWorkflow
from claude_agent_sdk_plugin.offline import Answer, offline_api_without_key, tool_use

TOOL_USE_ID = "toolu_hello"


def tool_result(request: dict[str, Any]) -> dict[str, Any]:
    return next(
        block
        for message in request["messages"]
        if isinstance(message["content"], list)
        for block in message["content"]
        if block.get("tool_use_id") == TOOL_USE_ID
    )


def after_decision(request: dict[str, Any]) -> str:
    if tool_result(request).get("is_error"):
        return "Understood. I did not create hello.txt."
    return "Created hello.txt."


OFFLINE_ANSWERS: dict[str, Answer] = {
    f"tool_result:{TOOL_USE_ID}": after_decision,
    "hello.txt": tool_use(
        TOOL_USE_ID, "Bash", command="echo 'Hello from Claude Code' > hello.txt"
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
            task_queue="claude-agent-sdk-human-in-the-loop",
            workflows=[HumanInTheLoopWorkflow],
            plugins=[ClaudeAgentSDKPlugin()],
        ):
            print(f"Worker started. To stop it gracefully: kill {os.getpid()}")
            await stop.wait()


if __name__ == "__main__":
    asyncio.run(main())
