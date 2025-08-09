from temporalio import workflow

from .mcp_server.nexus_service import MCPServerNexusService, MCPServerStartInput
from .minimal_mcp_client import MinimalMCPClient


@workflow.defn(sandboxed=False)  # MCP requires anyio/sniffio
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

        # Start the MCP server workflow
        op_handle = await nexus_client.start_operation(
            MCPServerNexusService.start,
            MCPServerStartInput(
                mcp_server_workflow_name="SequentialThinkingMCPServerWorkflow"
            ),
        )
        workflow.logger.info(
            f"Started MCP server workflow, token: {op_handle.operation_token}"
        )
        assert op_handle.operation_token

        # Create minimal MCP client that works in Temporal workflows
        mcp = MinimalMCPClient(nexus_client, op_handle.operation_token)

        # Initialize the client
        await mcp.initialize()
        workflow.logger.info("Initialized MCP client")

        # List available tools
        tools_result = await mcp.list_tools()
        workflow.logger.info(f"Listed tools: {tools_result}")
        print("\nAvailable tools:")
        for tool in tools_result.tools:
            assert tool.description
            print(f"  - {tool.name}: {tool.description[:60]}...")

        # Call the sequential thinking tool
        result = await mcp.call_tool(
            "sequentialthinking",
            arguments={
                "thought": "What is the capital of France?",
                "thoughtNumber": 1,
                "totalThoughts": 1,
                "nextThoughtNeeded": False,
            },
        )

        workflow.logger.info(f"Tool call result: {result}")
        print("\nTool result:")
        print(result)

        return f"Completed MCP interaction. Final result: {result}"
