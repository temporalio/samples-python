import asyncio
import os
import signal

from temporalio.claude_agent_sdk import ClaudeAgentSDKPlugin
from temporalio.client import Client
from temporalio.worker import Worker

from claude_agent_sdk_plugin.multi_agent.workflow import MultiAgentWorkflow
from claude_agent_sdk_plugin.offline import Answer, offline_api_without_key, tool_use

RESEARCH_NOTES = "- Workflows are durable.\n- Activities are retried.\n- Signals are delivered exactly once."
BRIEFING = "Temporal keeps your code running through failures."


OFFLINE_ANSWERS: dict[str, Answer] = {
    "short briefing on this topic": tool_use(
        "toolu_research",
        "Agent",
        description="Research the topic",
        subagent_type="researcher",
        prompt="Collect three key facts about the topic.",
        run_in_background=False,
    ),
    "Collect three key facts": RESEARCH_NOTES,
    "tool_result:toolu_research": tool_use(
        "toolu_write",
        "Agent",
        description="Write the briefing",
        subagent_type="writer",
        prompt="Turn these notes into a one-sentence briefing.",
        run_in_background=False,
    ),
    "Turn these notes": BRIEFING,
    "tool_result:toolu_write": f"Final briefing: {BRIEFING}",
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
            task_queue="claude-agent-sdk-multi-agent",
            workflows=[MultiAgentWorkflow],
            plugins=[ClaudeAgentSDKPlugin()],
        ):
            print(f"Worker started. To stop it gracefully: kill {os.getpid()}")
            await stop.wait()


if __name__ == "__main__":
    asyncio.run(main())
