from __future__ import annotations

from agents import Agent, Runner, trace
from agents.mcp import MCPServer
from agents.model_settings import ModelSettings
from temporalio import workflow
from temporalio.contrib import openai_agents


@workflow.defn
class StreamableHttpWorkflow:
    @workflow.run
    async def run(self) -> str:
        with trace(workflow_name="MCP Streamable HTTP Example"):
            server: MCPServer = openai_agents.workflow.stateless_mcp_server(
                "StreamableHttpServer"
            )
            agent = Agent(
                name="Assistant",
                instructions="Use the tools to answer the questions.",
                mcp_servers=[server],
                model_settings=ModelSettings(tool_choice="required"),
            )

            # Use the `add` tool to add two numbers
            message = "Add these numbers: 7 and 22."
            workflow.logger.info(f"Running: {message}")
            result1 = await Runner.run(starting_agent=agent, input=message)

            # Run the `get_weather` tool
            message = "What's the weather in Tokyo?"
            workflow.logger.info(f"Running: {message}")
            result2 = await Runner.run(starting_agent=agent, input=message)

            # Run the `get_secret_word` tool
            message = "What's the secret word?"
            workflow.logger.info(f"Running: {message}")
            result3 = await Runner.run(starting_agent=agent, input=message)

            return f"{result1.final_output}\n\n{result2.final_output}\n\n{result3.final_output}"
