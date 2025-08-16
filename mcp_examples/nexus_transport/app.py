import asyncio
import json
import os
import uuid
from typing import cast

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import TextContent
from temporalio import workflow
from temporalio.client import Client
from temporalio.worker import UnsandboxedWorkflowRunner, Worker

from mcp_examples.common.mcp_sdk_nexus_transport import NexusTransport
from mcp_examples.common.mcp_server_nexus_service import (
    MCPServerNexusService,
    MCPServerNexusServiceHandler,
)


async def create_client_session_and_call_tool_using_standard_transport():
    server_params = StdioServerParameters(
        command="npx", args=["-y", "@modelcontextprotocol/server-sequential-thinking"]
    )

    async with stdio_client(server_params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            await _call_tool(session)


async def create_client_session_and_call_tool_using_nexus_transport(
    nexus_client: workflow.NexusClient[MCPServerNexusService],
):
    transport = NexusTransport(nexus_client, "mcp-sequential-thinking-nexus-endpoint")

    async with transport.connect() as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            await _call_tool(session)


@workflow.defn
class CallToolWorkflow:
    def __init__(self):
        print("Creating nexus client in workflow...")
        self.nexus_client = workflow.create_nexus_client(
            service=MCPServerNexusService,
            endpoint="mcp-sequential-thinking-nexus-endpoint",
        )
        print("Nexus client created")

    @workflow.run
    async def run(self):
        await create_client_session_and_call_tool_using_nexus_transport(
            self.nexus_client
        )


async def main():
    client = await Client.connect("localhost:7233")
    async with Worker(
        client,
        task_queue="mcp-sequential-thinking-task-queue",
        workflows=[
            CallToolWorkflow,
        ],
        nexus_service_handlers=[MCPServerNexusServiceHandler()],
        workflow_runner=UnsandboxedWorkflowRunner(),
    ) as worker:
        await client.execute_workflow(
            CallToolWorkflow.run,
            id=str(uuid.uuid4()),
            task_queue=worker.task_queue,
        )


async def _call_tool(session: ClientSession):
    tools = await session.list_tools()
    print(f"Available tools: {[tool.name for tool in tools.tools]}")

    tool_input = {
        "thought": "To solve a complex problem, I need to break it down into steps",
        "thoughtNumber": 1,
        "totalThoughts": 3,
        "nextThoughtNeeded": True,
    }

    print(f"\nInput: {json.dumps(tool_input, indent=2)}")

    result = await session.call_tool("sequentialthinking", tool_input)
    content = cast(list[TextContent], result.content)

    print(f"\nOutput: {content[0]}")


if __name__ == "__main__":
    print("Starting app...")
    if "WITHOUT_WORKFLOW" in os.environ:
        asyncio.run(create_client_session_and_call_tool_using_standard_transport())
    else:
        asyncio.run(main())
