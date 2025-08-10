"""
Experimental agent workflow that uses the standard MCP ClientSession with Nexus transport.
This patches the Temporal event loop to work with anyio/sniffio.
"""

from temporalio import workflow

from .event_loop_patch import patch_temporal_event_loop
from .mcp_server.nexus_service import MCPServerNexusService, MCPServerStartInput
from .nexus_transport import create_nexus_mcp_session


@workflow.defn(sandboxed=False)  # Required for MCP and anyio
class AgentWorkflowWithTransport:
    @workflow.run
    async def run(self):
        workflow.logger.info("AgentWorkflowWithTransport started")

        # Patch Temporal's event loop to work with anyio
        # The issue: get_task_factory() exists but raises NotImplementedError
        patch_temporal_event_loop()

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

        error_msg = None
        try:
            workflow.logger.info("Creating Nexus MCP session...")
            # Use the standard MCP ClientSession with Nexus transport
            async with create_nexus_mcp_session(
                nexus_client, op_handle.operation_token
            ) as session:
                workflow.logger.info("Created MCP session with Nexus transport")

                # Use standard MCP client API
                tools_response = await session.list_tools()
                workflow.logger.info(f"Listed tools: {tools_response}")

                # Extract tools from response
                tools = []
                for item in tools_response:
                    if isinstance(item, tuple) and item[0] == "tools":
                        tools.extend(item[1])

                print("\nAvailable tools:")
                for tool in tools:
                    print(f"  - {tool.name}: {tool.description[:60]}...")

                # Call the sequential thinking tool using standard API
                result = await session.call_tool(
                    "sequentialthinking",
                    arguments={
                        "thought": "What is the capital of France? Let me think step by step.",
                        "thoughtNumber": 1,
                        "totalThoughts": 2,
                        "nextThoughtNeeded": True,
                    },
                )

                workflow.logger.info(f"First tool result: {result}")

                # Second call
                result2 = await session.call_tool(
                    "sequentialthinking",
                    arguments={
                        "thought": "The capital of France is Paris. It's been the capital for centuries.",
                        "thoughtNumber": 2,
                        "totalThoughts": 2,
                        "nextThoughtNeeded": False,
                    },
                )

                workflow.logger.info(f"Second tool result: {result2}")
                print("\nFinal result:")
                print(result2)

                return f"Completed using standard MCP ClientSession. Final result: {result2}"

        except Exception as e:
            import traceback

            error_detail = traceback.format_exc()
            error_msg = f"{type(e).__name__}: {str(e)}"
            workflow.logger.error(
                f"Error using MCP transport: {error_msg}\n{error_detail}"
            )

        if error_msg:
            return f"Failed with error: {error_msg}"
        return "Unexpected completion without result"
