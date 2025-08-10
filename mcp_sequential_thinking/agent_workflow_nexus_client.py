from temporalio import workflow

from .mcp_server.nexus_service import MCPServerNexusService
from .nexus_client import NexusMCPClientSession


@workflow.defn(sandboxed=False)
class AgentWorkflowNexusClient:
    @workflow.run
    async def run(self):
        nexus_client = workflow.create_nexus_client(
            service=MCPServerNexusService,
            endpoint="mcp-sequential-thinking-nexus-endpoint",
        )

        mcp = NexusMCPClientSession(nexus_client)

        init_result = await mcp.initialize()

        tools_result = await mcp.list_tools()

        result1 = await mcp.call_tool(
            "sequentialthinking",
            arguments={
                "thought": "To find the capital of France, I need to recall my knowledge of European geography.",
                "thoughtNumber": 1,
                "totalThoughts": 2,
                "nextThoughtNeeded": True,
            },
        )

        result2 = await mcp.call_tool(
            "sequentialthinking",
            arguments={
                "thought": "The capital of France is Paris. It has been the capital city for centuries and is known for landmarks like the Eiffel Tower.",
                "thoughtNumber": 2,
                "totalThoughts": 2,
                "nextThoughtNeeded": False,
            },
        )

        return f"Completed MCP interaction. Final result: {result2}"
