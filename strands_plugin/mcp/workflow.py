"""Workflow that uses an MCP server through ``TemporalMCPClient``.

``TemporalMCPClient`` on the workflow side is a pure handle that references
the server by name and carries the activity options for each MCP call. The
agent lists the server's tools in an activity before each model call, and
runs each tool call in another activity.
"""

# @@@SNIPSTART python-strands-mcp-workflow
from datetime import timedelta

from temporalio import workflow
from temporalio.strands_agents import TemporalAgent, TemporalMCPClient


@workflow.defn
class MCPWorkflow:
    def __init__(self) -> None:
        echo = TemporalMCPClient(
            server="echo",
            start_to_close_timeout=timedelta(seconds=30),
        )
        self.agent = TemporalAgent(
            start_to_close_timeout=timedelta(seconds=60),
            tools=[echo],
        )

    @workflow.run
    async def run(self, prompt: str) -> str:
        result = await self.agent.invoke_async(prompt)
        return str(result)


# @@@SNIPEND
