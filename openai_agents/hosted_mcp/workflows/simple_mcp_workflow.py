from __future__ import annotations

from agents import Agent, HostedMCPTool, Runner
from temporalio import workflow


@workflow.defn
class SimpleMCPWorkflow:
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
                        "require_approval": "never",
                    }
                )
            ],
        )

        result = await Runner.run(agent, question)
        return result.final_output
