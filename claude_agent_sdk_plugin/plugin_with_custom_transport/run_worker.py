import asyncio
import os

from temporalio.claude_agent_sdk import ClaudeAgentSDKPlugin
from temporalio.client import Client
from temporalio.worker import Worker

from claude_agent_sdk_plugin.offline import Answer, offline_api_without_key, tool_use
from claude_agent_sdk_plugin.plugin_with_custom_transport.connector import (
    SandboxConnector,
)
from claude_agent_sdk_plugin.plugin_with_custom_transport.workflow import (
    COUNT_SYLLABLES,
    PLUGIN_DIR,
    PluginWithCustomTransportWorkflow,
)

# The plugin on the Worker. The sandbox starts with a clean filesystem, so the
# connector copies the whole directory into each sandbox before Claude Code starts.
LOCAL_PLUGIN_DIR = os.path.join(os.path.dirname(__file__), "haiku-writer")

HAIKU = "Workers fall and rise\nhistory remembers all\nthe work carries on"

OFFLINE_ANSWERS: dict[str, Answer] = {
    "tool_result:toolu_count": f"{HAIKU}\n\n~ haiku-writer",
    "tool_result:toolu_skill": tool_use("toolu_count", COUNT_SYLLABLES, text=HAIKU),
    "haiku": tool_use("toolu_skill", "Skill", skill="haiku-writer:haiku"),
}


async def main() -> None:
    client = await Client.connect(os.environ.get("TEMPORAL_ADDRESS", "localhost:7233"))

    with offline_api_without_key(OFFLINE_ANSWERS):
        worker = Worker(
            client,
            task_queue="claude-agent-sdk-plugin-with-custom-transport",
            workflows=[PluginWithCustomTransportWorkflow],
            plugins=[
                ClaudeAgentSDKPlugin(
                    connector=SandboxConnector(uploads={PLUGIN_DIR: LOCAL_PLUGIN_DIR})
                )
            ],
        )
        await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
