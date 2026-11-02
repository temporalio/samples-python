import asyncio
import os

from temporalio.claude_agent_sdk import ClaudeAgentSDKPlugin
from temporalio.client import Client
from temporalio.worker import Worker

from claude_agent_sdk_plugin.hooks.workflow import HooksWorkflow, audit_command
from claude_agent_sdk_plugin.offline import Answer, offline_api_without_key, tool_use

OFFLINE_ANSWERS: dict[str, Answer] = {
    "tool_result:toolu_delete": "The command that deletes hello.txt was blocked.",
    "tool_result:toolu_echo": tool_use("toolu_delete", "Bash", command="rm hello.txt"),
    "hello.txt": tool_use("toolu_echo", "Bash", command="echo hello"),
}


async def main() -> None:
    client = await Client.connect(os.environ.get("TEMPORAL_ADDRESS", "localhost:7233"))

    with offline_api_without_key(OFFLINE_ANSWERS):
        worker = Worker(
            client,
            task_queue="claude-agent-sdk-hooks",
            workflows=[HooksWorkflow],
            activities=[audit_command],
            plugins=[ClaudeAgentSDKPlugin()],
        )
        await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
