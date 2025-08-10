from temporalio import workflow

from .mcp_server.nexus_service import MCPServerNexusService
from .minimal_mcp_client import NexusMCPClientSession


@workflow.defn(sandboxed=False)  # Imports mcp package
class AgentWorkflow:
    @workflow.run
    async def run(self):
        workflow.logger.info("AgentWorkflow started")

        # Create Nexus client for the MCP server
        nexus_client = workflow.create_nexus_client(
            service=MCPServerNexusService,
            endpoint="mcp-sequential-thinking-nexus-endpoint",
        )
        workflow.logger.info("Created Nexus client")

        # Create minimal MCP client that works in Temporal workflows
        mcp = NexusMCPClientSession(nexus_client)

        # Initialize the client - this starts the MCP server workflow
        init_result = await mcp.initialize()
        workflow.logger.info(
            f"Initialized MCP client with server: {init_result.serverInfo.name} v{init_result.serverInfo.version}"
        )

        # List available tools
        tools_result = await mcp.list_tools()
        workflow.logger.info(f"Listed tools: {tools_result}")
        print("\nAvailable tools:")
        for tool in tools_result.tools:
            assert tool.description, f"Tool {tool.name} missing description"
            print(f"  - {tool.name}: {tool.description[:60]}...")

        # Call the sequential thinking tool with multiple steps
        # Step 1
        result1 = await mcp.call_tool(
            "sequentialthinking",
            arguments={
                "thought": "To find the capital of France, I need to recall my knowledge of European geography.",
                "thoughtNumber": 1,
                "totalThoughts": 2,
                "nextThoughtNeeded": True,
            },
        )
        workflow.logger.info(f"First thought result: {result1}")

        # Step 2
        result = await mcp.call_tool(
            "sequentialthinking",
            arguments={
                "thought": "The capital of France is Paris. It has been the capital city for centuries and is known for landmarks like the Eiffel Tower.",
                "thoughtNumber": 2,
                "totalThoughts": 2,
                "nextThoughtNeeded": False,
            },
        )

        workflow.logger.info(f"Tool call result: {result}")
        print("\nTool result:")
        print(result)

        return f"Completed MCP interaction. Final result: {result}"
