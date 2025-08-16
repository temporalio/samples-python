"""
A Nexus service that presents the interface of an MCP server.
It is backed by a Temporal workflow.
"""

import uuid
from dataclasses import dataclass

import nexusrpc
from mcp import StdioServerParameters
from mcp.types import (
    CallToolRequest,
    CallToolResult,
    ListToolsRequest,
    ListToolsResult,
)
from temporalio import nexus


@dataclass
class MCPServerStartInput:
    mcp_server_workflow_name: str
    mcp_server_params: StdioServerParameters


@dataclass
class ListToolsInput:
    operation_token: str
    request: ListToolsRequest


@dataclass
class CallToolInput:
    operation_token: str
    request: CallToolRequest


@nexusrpc.service
class MCPServerNexusService:
    start: nexusrpc.Operation[MCPServerStartInput, None]
    list_tools: nexusrpc.Operation[ListToolsInput, ListToolsResult]
    call_tool: nexusrpc.Operation[CallToolInput, CallToolResult]


@nexusrpc.handler.service_handler(service=MCPServerNexusService)
class MCPServerNexusServiceHandler:
    @nexus.workflow_run_operation
    async def start(
        self, ctx: nexus.WorkflowRunOperationContext, input: MCPServerStartInput
    ) -> nexus.WorkflowHandle[None]:
        return await ctx.start_workflow(
            input.mcp_server_workflow_name,
            input.mcp_server_params,
            id=str(uuid.uuid4()),
            task_queue="mcp-sequential-thinking-task-queue",
        )

    @nexusrpc.handler.sync_operation
    async def call_tool(
        self, ctx: nexusrpc.handler.StartOperationContext, input: CallToolInput
    ) -> CallToolResult:
        workflow_handle = nexus.WorkflowHandle.from_token(
            input.operation_token
        )._to_client_workflow_handle(nexus.client())
        return await workflow_handle.execute_update("call_tool", input.request)

    @nexusrpc.handler.sync_operation
    async def list_tools(
        self, ctx: nexusrpc.handler.StartOperationContext, input: ListToolsInput
    ) -> ListToolsResult:
        workflow_handle = nexus.WorkflowHandle.from_token(
            input.operation_token
        )._to_client_workflow_handle(nexus.client())
        return await workflow_handle.execute_update("list_tools", input.request)
