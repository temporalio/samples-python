from __future__ import annotations

from agents import Agent, Runner, trace
from agents.model_settings import ModelSettings
from temporalio import workflow
from temporalio.openai_agents.workflow import temporal_mcp_server

MCP_SERVER_NAME = "StreamableHttpV2Server"
TASK_QUEUE = "openai-agents-mcp-streamable-http-v2-task-queue"


@workflow.defn
class StreamableHttpV2Workflow:
    @workflow.run
    async def run(self) -> str:
        with trace(workflow_name="MCP v2 Streamable HTTP Example"):
            server = temporal_mcp_server(MCP_SERVER_NAME)
            agent = Agent(
                name="Assistant",
                instructions="Use the tools to answer the questions.",
                mcp_servers=[server],
                model_settings=ModelSettings(tool_choice="required"),
            )

            message = "Add these numbers: 7 and 22."
            workflow.logger.info("Running: %s", message)
            result1 = await Runner.run(starting_agent=agent, input=message)

            message = "What's the weather in Tokyo?"
            workflow.logger.info("Running: %s", message)
            result2 = await Runner.run(starting_agent=agent, input=message)

            message = "What's the secret word?"
            workflow.logger.info("Running: %s", message)
            result3 = await Runner.run(starting_agent=agent, input=message)

            return f"{result1.final_output}\n\n{result2.final_output}\n\n{result3.final_output}"
