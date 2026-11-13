"""Worker for the OpenTelemetry sample."""

# @@@SNIPSTART python-agent-framework-open-telemetry-worker
import asyncio
import os

from agent_framework.openai import OpenAIChatClient
from openai import AsyncOpenAI
from temporalio.agent_framework import AgentFrameworkPlugin
from temporalio.client import Client
from temporalio.contrib.opentelemetry import OpenTelemetryPlugin
from temporalio.worker import Worker

from agent_framework_plugin.open_telemetry.telemetry import install_tracer_provider
from agent_framework_plugin.open_telemetry.workflow import TracedWorkflow


def openai_chat_client() -> OpenAIChatClient:
    return OpenAIChatClient(
        model="gpt-4o-mini", async_client=AsyncOpenAI(max_retries=0)
    )


async def main() -> None:
    if not os.environ.get("OPENAI_API_KEY"):
        raise SystemExit("Set OPENAI_API_KEY before starting the Worker.")

    # Set the provider before connecting; the plugins read it at startup.
    install_tracer_provider("agent-framework-worker")
    plugin = AgentFrameworkPlugin(chat_clients={"gpt-4o-mini": openai_chat_client})
    # The Worker inherits the Client's plugins in this order: tracing first.
    client = await Client.connect(
        os.environ.get("TEMPORAL_ADDRESS", "localhost:7233"),
        plugins=[OpenTelemetryPlugin(add_temporal_spans=True), plugin],
    )

    worker = Worker(
        client,
        task_queue="agent-framework-open-telemetry",
        workflows=[TracedWorkflow],
    )
    print("Worker started. Ctrl+C to exit.")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
# @@@SNIPEND
