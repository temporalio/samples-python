import asyncio

from temporalio.client import Client
from temporalio.worker import Worker

from mcp_sequential_thinking.agent_workflow import AgentWorkflow
from mcp_sequential_thinking.mcp_server.nexus_service import (
    MCPServerNexusServiceHandler,
)
from mcp_sequential_thinking.mcp_server.workflow import (
    SequentialThinkingMCPServerWorkflow,
)


async def main():
    client = await Client.connect("localhost:7233")
    worker = Worker(
        client,
        task_queue="mcp-sequential-thinking-task-queue",
        workflows=[AgentWorkflow, SequentialThinkingMCPServerWorkflow],
        nexus_service_handlers=[MCPServerNexusServiceHandler()],
    )
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
