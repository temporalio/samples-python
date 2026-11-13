"""Worker for the structured output sample."""

# @@@SNIPSTART python-agent-framework-structured-output-worker
import asyncio
import os

from agent_framework.openai import OpenAIChatClient
from openai import AsyncOpenAI
from temporalio.agent_framework import AgentFrameworkPlugin
from temporalio.client import Client
from temporalio.worker import Worker

from agent_framework_plugin.structured_output.workflow import StructuredOutputWorkflow


def openai_chat_client() -> OpenAIChatClient:
    return OpenAIChatClient(
        model="gpt-4o-mini", async_client=AsyncOpenAI(max_retries=0)
    )


async def main() -> None:
    if not os.environ.get("OPENAI_API_KEY"):
        raise SystemExit("Set OPENAI_API_KEY before starting the Worker.")

    plugin = AgentFrameworkPlugin(chat_clients={"gpt-4o-mini": openai_chat_client})
    client = await Client.connect(
        os.environ.get("TEMPORAL_ADDRESS", "localhost:7233"),
        plugins=[plugin],
    )

    worker = Worker(
        client,
        task_queue="agent-framework-structured-output",
        workflows=[StructuredOutputWorkflow],
    )
    print("Worker started. Ctrl+C to exit.")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
# @@@SNIPEND
