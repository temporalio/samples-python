import asyncio
import os
import signal

from temporalio.claude_agent_sdk import ClaudeAgentSDKPlugin
from temporalio.client import Client
from temporalio.worker import Worker

from claude_agent_sdk_plugin.fork_session.workflow import ForkSessionWorkflow
from claude_agent_sdk_plugin.offline import offline_api_without_key

OFFLINE_ANSWERS = {
    "Plan a weekend in Lisbon": "Saturday: Alfama and a fado show. Sunday: Belém.",
    "on a tight budget": "Walk Alfama, catch a free fado night, take the tram to Belém.",
    "with no budget limit": "A private fado dinner, then a yacht along the Tagus to Belém.",
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
            task_queue="claude-agent-sdk-fork-session",
            workflows=[ForkSessionWorkflow],
            plugins=[ClaudeAgentSDKPlugin()],
        ):
            print(f"Worker started. To stop it gracefully: kill {os.getpid()}")
            await stop.wait()


if __name__ == "__main__":
    asyncio.run(main())
