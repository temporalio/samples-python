import asyncio
import os
import signal

from temporalio.claude_agent_sdk import ClaudeAgentSDKPlugin
from temporalio.client import Client
from temporalio.contrib.pydantic import pydantic_data_converter
from temporalio.worker import Worker

from claude_agent_sdk_plugin.offline import offline_api_without_key, tool_use
from claude_agent_sdk_plugin.structured_output.workflow import TriageTicketWorkflow

OFFLINE_ANSWERS = {
    "Triage this customer message": tool_use(
        "toolu_ticket",
        "StructuredOutput",
        category="bug",
        priority=2,
        summary="The settings page crashes the app when opened.",
    )
}


async def main() -> None:
    # The Pydantic converter lets the Workflow return a SupportTicket.
    client = await Client.connect(
        os.environ.get("TEMPORAL_ADDRESS", "localhost:7233"),
        data_converter=pydantic_data_converter,
    )

    # Shut the Worker down on SIGTERM, so the plugin stops Claude Code and a
    # restarted Worker can resume its session.
    stop = asyncio.Event()
    asyncio.get_running_loop().add_signal_handler(signal.SIGTERM, stop.set)

    with offline_api_without_key(OFFLINE_ANSWERS):
        async with Worker(
            client,
            task_queue="claude-agent-sdk-structured-output",
            workflows=[TriageTicketWorkflow],
            plugins=[ClaudeAgentSDKPlugin()],
        ):
            print(f"Worker started. To stop it gracefully: kill {os.getpid()}")
            await stop.wait()


if __name__ == "__main__":
    asyncio.run(main())
