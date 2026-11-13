"""Worker for the MCP sample. It starts ``echo_mcp_server.py`` on demand."""

# @@@SNIPSTART python-agent-framework-mcp-worker
import asyncio
import os
import sys
from pathlib import Path

from agent_framework.openai import OpenAIChatClient
from mcp import Client as MCPClient
from mcp import StdioServerParameters, stdio_client
from openai import AsyncOpenAI
from temporalio.agent_framework import AgentFrameworkPlugin
from temporalio.client import Client
from temporalio.worker import Worker

from workflow import MCPWorkflow

ECHO_SERVER = Path(__file__).parent / "echo_mcp_server.py"


def openai_chat_client() -> OpenAIChatClient:
    return OpenAIChatClient(
        model="gpt-4o-mini", async_client=AsyncOpenAI(max_retries=0)
    )


def echo_mcp_client() -> MCPClient:
    # Runs on the Worker. The plugin connects on the first MCP Activity and
    # keeps the connection for 5 minutes of idleness.
    return MCPClient(
        stdio_client(
            StdioServerParameters(command=sys.executable, args=[str(ECHO_SERVER)])
        )
    )


async def main() -> None:
    if not os.environ.get("OPENAI_API_KEY"):
        raise SystemExit("Set OPENAI_API_KEY before starting the Worker.")

    plugin = AgentFrameworkPlugin(
        chat_clients={"gpt-4o-mini": openai_chat_client},
        mcp_clients={"echo": echo_mcp_client},
    )
    client = await Client.connect(
        os.environ.get("TEMPORAL_ADDRESS", "localhost:7233"),
        plugins=[plugin],
    )

    worker = Worker(
        client,
        task_queue="agent-framework-mcp",
        workflows=[MCPWorkflow],
    )
    print("Worker started. Ctrl+C to exit.")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
# @@@SNIPEND
