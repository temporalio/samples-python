from mcp.types import CallToolRequest, CallToolRequestParams
from temporalio import workflow

from .mcp_server.nexus_service import (
    CallToolInput,
    MCPServerNexusService,
    MCPServerStartInput,
)


@workflow.defn(sandboxed=False)
class AgentWorkflow:
    @workflow.run
    async def run(self):
        nexus_client = workflow.create_nexus_client(
            service=MCPServerNexusService,
            endpoint="mcp-sequential-thinking-nexus-endpoint",
        )
        op_handle = await nexus_client.start_operation(
            MCPServerNexusService.start,
            MCPServerStartInput(
                mcp_server_workflow_name="SequentialThinkingMCPServerWorkflow"
            ),
        )
        assert op_handle.operation_token
        tool_result = await nexus_client.execute_operation(
            MCPServerNexusService.call_tool,
            CallToolInput(
                operation_token=op_handle.operation_token,
                request=CallToolRequest(
                    method="tools/call",
                    params=CallToolRequestParams(
                        name="sequentialthinking",
                        arguments={
                            "thought": "What is the capital of France?",
                            "thoughtNumber": 1,
                            "totalThoughts": 1,
                            "nextThoughtNeeded": False,
                        },
                    ),
                ),
            ),
        )
        print("\n\ntool call result:\n\n")
        print(tool_result)
