import asyncio
import json
import uuid
from enum import Enum
from typing import cast

import typer
from mcp import ClientSession, StdioServerParameters
from mcp.types import TextContent
from temporalio import workflow
from temporalio.client import Client
from temporalio.contrib.pydantic import pydantic_data_converter
from temporalio.worker import UnsandboxedWorkflowRunner, Worker

from mcp_examples.workflow_nexus_transport.mcp_server_nexus_service import (
    MCPServerInput,
    MCPServerNexusServiceHandler,
    MCPServiceWorkflowBase,
)
from mcp_examples.workflow_nexus_transport.stdio_mcp_server.activity import (
    run_stdio_mcp_server,
)
from mcp_examples.workflow_nexus_transport.stdio_mcp_server.workflow import (
    MCPStdioClientSessionWorkflow,
)
from mcp_examples.workflow_nexus_transport.workflow_mcp_server.workflow import (
    SequentialThinkingMCPServerWorkflow,
)
from mcp_examples.workflow_nexus_transport.workflow_transport import WorkflowTransport

app = typer.Typer()


@workflow.defn
class MCPCallerWorkflow:
    @workflow.run
    async def run(self, input: MCPServerInput):
        transport = WorkflowTransport(
            endpoint="mcp-sequential-thinking-nexus-endpoint", input=input
        )

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


class MCPServerType(str, Enum):
    stdio = "stdio"
    workflow = "workflow"


async def run_caller_workflow(
    mcp_server_workflow_cls: type[MCPServiceWorkflowBase],
    mcp_server_params: StdioServerParameters | None,
):
    mcp_server_input = MCPServerInput(
        workflow_name=mcp_server_workflow_cls.__name__,
        stdio_server_params=mcp_server_params,
    )

    client = await Client.connect(
        "localhost:7233",
        data_converter=pydantic_data_converter,
    )
    async with Worker(
        client,
        task_queue="mcp-sequential-thinking-task-queue",
        workflows=[MCPCallerWorkflow, mcp_server_workflow_cls],
        activities=[run_stdio_mcp_server],
        nexus_service_handlers=[MCPServerNexusServiceHandler()],
        workflow_runner=UnsandboxedWorkflowRunner(),
    ) as worker:
        await client.execute_workflow(
            MCPCallerWorkflow.run,
            mcp_server_input,
            id=str(uuid.uuid4()),
            task_queue=worker.task_queue,
        )


@app.command()
def main(
    mcp_server_type: MCPServerType = typer.Option(
        MCPServerType.stdio,
        "--mcp-server-type",
        help="MCP server type to use: 'stdio' for the official stdio server or 'workflow' for the MCP server implemented as a Temporal workflow",
    ),
):
    match mcp_server_type:
        case MCPServerType.stdio:
            workflow_cls = MCPStdioClientSessionWorkflow
            server_params = StdioServerParameters(
                command="npx",
                args=["-y", "@modelcontextprotocol/server-sequential-thinking"],
            )

        case MCPServerType.workflow:
            workflow_cls = SequentialThinkingMCPServerWorkflow
            server_params = None

    asyncio.run(run_caller_workflow(workflow_cls, server_params))


if __name__ == "__main__":
    app()
