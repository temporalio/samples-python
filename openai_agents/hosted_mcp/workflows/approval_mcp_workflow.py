from __future__ import annotations

from agents import (
    Agent,
    HostedMCPTool,
    MCPToolApprovalFunctionResult,
    MCPToolApprovalRequest,
    Runner,
)
from temporalio import workflow


def approval_callback(request: MCPToolApprovalRequest) -> MCPToolApprovalFunctionResult:
    """Simple approval callback that logs the request and approves by default.

    In a real application, user input would be provided through a UI or API.
    The approval callback executes within the Temporal workflow, so the application
    can use signals or updates to receive user input.
    """
    workflow.logger.info(f"MCP tool approval requested for: {request.data.name}")

    result: MCPToolApprovalFunctionResult = {"approve": True}
    return result


@workflow.defn
class ApprovalMCPWorkflow:
    @workflow.run
    async def run(
        self, question: str, server_url: str = "https://gitmcp.io/openai/codex"
    ) -> str:
        agent = Agent(
            name="Assistant",
            tools=[
                HostedMCPTool(
                    tool_config={
                        "type": "mcp",
                        "server_label": "gitmcp",
                        "server_url": server_url,
                        "require_approval": "always",
                    },
                    on_approval_request=approval_callback,
                )
            ],
        )

        result = await Runner.run(agent, question)
        return result.final_output
