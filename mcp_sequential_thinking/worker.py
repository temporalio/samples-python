import asyncio

from temporalio.client import Client
from temporalio.worker import Worker

from mcp_sequential_thinking.agent_workflow_nexus_client import (
    AgentWorkflowNexusClient,
)
from mcp_sequential_thinking.agent_workflow_with_llm import AgentWorkflowWithLLM
from mcp_sequential_thinking.llm_activity import call_llm, parse_json_response
from mcp_sequential_thinking.mcp_server.nexus_service import (
    MCPServerNexusServiceHandler,
)
from mcp_sequential_thinking.mcp_server.workflow import (
    SequentialThinkingMCPServerWorkflow,
)


async def main():
    client = await Client.connect("localhost:7233")
    async with Worker(
        client,
        task_queue="mcp-sequential-thinking-task-queue",
        workflows=[
            AgentWorkflowNexusClient,
            AgentWorkflowWithLLM,
            SequentialThinkingMCPServerWorkflow,
        ],
        activities=[call_llm, parse_json_response],
        nexus_service_handlers=[MCPServerNexusServiceHandler()],
    ):
        print("Worker started, press Ctrl+C to exit")
        await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
