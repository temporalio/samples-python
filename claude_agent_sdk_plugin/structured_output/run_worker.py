import asyncio
import os

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
    with offline_api_without_key(OFFLINE_ANSWERS):
        worker = Worker(
            client,
            task_queue="claude-agent-sdk-structured-output",
            workflows=[TriageTicketWorkflow],
            plugins=[ClaudeAgentSDKPlugin()],
        )
        print("Worker started. Ctrl+C to exit.")
        await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
