import asyncio

from temporalio.client import Client
from temporalio.worker import Worker

from mcp_sequential_thinking.mcp_server.nexus_service import (
    MCPServerNexusServiceHandler,
)
from mcp_sequential_thinking.mcp_server.workflow import (
    SequentialThinkingMCPServerWorkflow,
)

NAMESPACE = "mcp-sequential-thinking-handler-namespace"


async def main():
    client = await Client.connect("localhost:7233", namespace=NAMESPACE)
    async with Worker(
        client,
        task_queue="mcp-sequential-thinking-task-queue",
        workflows=[SequentialThinkingMCPServerWorkflow],
        nexus_service_handlers=[MCPServerNexusServiceHandler()],
    ) as worker:
        await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
