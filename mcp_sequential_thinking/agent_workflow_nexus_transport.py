from temporalio import workflow

from .event_loop_patch import patch_temporal_event_loop
from .mcp_server.nexus_service import MCPServerNexusService, MCPServerStartInput
from .nexus_transport import create_nexus_mcp_session


@workflow.defn(sandboxed=False)
class AgentWorkflowNexusTransport:
    @workflow.run
    async def run(self):
        patch_temporal_event_loop()

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

        try:
            async with create_nexus_mcp_session(
                nexus_client, op_handle.operation_token
            ) as session:
                tools_response = await session.list_tools()
                tools = []
                for item in tools_response:
                    if isinstance(item, tuple) and item[0] == "tools":
                        tools.extend(item[1])

                result = await session.call_tool(
                    "sequentialthinking",
                    arguments={
                        "thought": "What is the capital of France? Let me think step by step.",
                        "thoughtNumber": 1,
                        "totalThoughts": 2,
                        "nextThoughtNeeded": True,
                    },
                )

                result2 = await session.call_tool(
                    "sequentialthinking",
                    arguments={
                        "thought": "The capital of France is Paris. It's been the capital for centuries.",
                        "thoughtNumber": 2,
                        "totalThoughts": 2,
                        "nextThoughtNeeded": False,
                    },
                )

                return f"Completed using standard MCP ClientSession. Final result: {result2}"

        except Exception as e:
            return f"Failed with error: {type(e).__name__}: {str(e)}"
