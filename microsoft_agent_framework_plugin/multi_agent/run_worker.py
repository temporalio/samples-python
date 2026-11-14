"""Worker for the multi-agent sample."""

# @@@SNIPSTART python-microsoft-agent-framework-multi-agent-worker
import asyncio
import os

from agent_framework.openai import OpenAIChatClient
from openai import AsyncOpenAI
from temporalio.client import Client
from temporalio.microsoft_agent_framework import MicrosoftAgentFrameworkPlugin
from temporalio.worker import Worker

from microsoft_agent_framework_plugin.multi_agent.workflow import MultiAgentWorkflow


def openai_chat_client() -> OpenAIChatClient:
    return OpenAIChatClient(
        model="gpt-4o-mini", async_client=AsyncOpenAI(max_retries=0)
    )


async def main() -> None:
    if not os.environ.get("OPENAI_API_KEY"):
        raise SystemExit("Set OPENAI_API_KEY before starting the Worker.")

    # All three agents use the same model name; one factory serves them all.
    plugin = MicrosoftAgentFrameworkPlugin(
        chat_clients={"gpt-4o-mini": openai_chat_client}
    )
    client = await Client.connect(
        os.environ.get("TEMPORAL_ADDRESS", "localhost:7233"),
        plugins=[plugin],
    )

    worker = Worker(
        client,
        task_queue="microsoft-agent-framework-multi-agent",
        workflows=[MultiAgentWorkflow],
    )
    print("Worker started. Ctrl+C to exit.")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
# @@@SNIPEND
