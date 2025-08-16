import asyncio
import json
import uuid
from typing import cast

from mcp import ClientSession, StdioServerParameters
from mcp.types import TextContent
from temporalio import workflow
from temporalio.client import Client
from temporalio.contrib.pydantic import pydantic_data_converter
from temporalio.worker import UnsandboxedWorkflowRunner, Worker

from mcp_examples.nexus_transport.mcp_server_nexus_service import (
    MCPServerNexusService,
    MCPServerNexusServiceHandler,
)
from mcp_examples.nexus_transport.nexus_transport import NexusTransport
from mcp_examples.nexus_transport.stdio_mcp_server.activity import run_stdio_mcp_server
from mcp_examples.nexus_transport.stdio_mcp_server.workflow import (
    MCPStdioClientSessionWorkflow,
)


@workflow.defn
class MCPCallerWorkflow:
    @workflow.run
    async def run(self, server_params: StdioServerParameters):
        nexus_client = workflow.create_nexus_client(
            service=MCPServerNexusService,
            endpoint="mcp-sequential-thinking-nexus-endpoint",
        )
        transport = NexusTransport(nexus_client, server_params)

        async with transport.connect() as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
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


async def main(server_params: StdioServerParameters):
    client = await Client.connect(
        "localhost:7233",
        data_converter=pydantic_data_converter,
    )
    async with Worker(
        client,
        task_queue="mcp-sequential-thinking-task-queue",
        workflows=[
            MCPCallerWorkflow,
            MCPStdioClientSessionWorkflow,
        ],
        activities=[run_stdio_mcp_server],
        nexus_service_handlers=[MCPServerNexusServiceHandler()],
        workflow_runner=UnsandboxedWorkflowRunner(),
    ) as worker:
        await client.execute_workflow(
            MCPCallerWorkflow.run,
            server_params,
            id=str(uuid.uuid4()),
            task_queue=worker.task_queue,
        )


if __name__ == "__main__":
    server_params = StdioServerParameters(
        command="npx",
        args=["-y", "@modelcontextprotocol/server-sequential-thinking"],
    )
    asyncio.run(main(server_params))
