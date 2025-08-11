import mcp.client.session
from temporalio import workflow

from mcp_sequential_thinking.mcp_server.nexus_service import (
    MCPServerNexusService,
    MCPServerStartInput,
)
from mcp_sequential_thinking.nexus_transport import NexusTransport

from .event_loop_patch import patch_sdk_python_event_loop


@workflow.defn(sandboxed=False)
class AgentWorkflowNexusTransport:
    @workflow.run
    async def run(self):
        patch_sdk_python_event_loop()

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

        try:
            transport = NexusTransport(nexus_client, op_handle.operation_token)

            async with transport.connect() as (read_stream, write_stream):
                async with mcp.client.session.ClientSession(
                    read_stream, write_stream
                ) as session:
                    await session.initialize()
                    tools_response = await session.list_tools()
                    tools = []
                    for item in tools_response:
                        if isinstance(item, tuple) and item[0] == "tools":
                            tools.extend(item[1])

                    _result1 = await session.call_tool(
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
