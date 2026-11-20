"""MCP tools through ``TemporalMCPToolProvider``.

Before each run the provider lists the server's tools with the
``temporalio.mcp.echo.list-tools`` Activity and adds one tool per entry. Each
call the model makes runs the ``temporalio.mcp.echo.call-tool`` Activity. The
connection to the server lives on the Worker.
"""

# @@@SNIPSTART python-microsoft-agent-framework-mcp-workflow
from datetime import timedelta

from agent_framework import Agent
from temporalio import workflow
from temporalio.microsoft_agent_framework import (
    TemporalChatClient,
    TemporalMCPToolProvider,
)


@workflow.defn
class MCPWorkflow:
    @workflow.run
    async def run(self, prompt: str) -> str:
        agent = Agent(
            client=TemporalChatClient(
                "gpt-4o-mini", start_to_close_timeout=timedelta(seconds=60)
            ),
            instructions="Use the echo tool when asked to echo something.",
            context_providers=[
                TemporalMCPToolProvider(
                    "echo", start_to_close_timeout=timedelta(seconds=30)
                )
            ],
        )
        response = await agent.run(prompt)
        return response.text


# @@@SNIPEND
