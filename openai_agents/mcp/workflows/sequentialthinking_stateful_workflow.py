from __future__ import annotations

from agents import Agent, Runner, trace
from agents.model_settings import ModelSettings
from temporalio import workflow
from temporalio.contrib import openai_agents as temporal_openai_agents


@workflow.defn
class SequentialThinkingWorkflow:
    @workflow.run
    async def run(self) -> str:
        async with temporal_openai_agents.workflow.stateful_mcp_server(
            "SequentialThinkingServer",
        ) as server:
            with trace(workflow_name="MCP Sequential Thinking Example"):
                agent = Agent(
                    name="Assistant",
                    instructions=(
                        "You manage a sequential plan using available MCP tools."
                        " Create, update, and summarize a plan by invoking tools where appropriate."
                    ),
                    mcp_servers=[server],
                    model_settings=ModelSettings(tool_choice="required"),
                )

                # Initialize a plan
                message = (
                    "Initialize a 3-step plan for: 'Prepare a short blog post about Temporal workflows'."
                    " Then show the steps."
                )
                workflow.logger.info(f"Running: {message}")
                result1 = await Runner.run(starting_agent=agent, input=message)

                # Mark first step complete and show remaining
                message = "Mark the first step as complete. Then list remaining steps."
                workflow.logger.info(f"Running: {message}")
                result2 = await Runner.run(starting_agent=agent, input=message)

                # Add a new step and summarize
                message = "Add one more step: 'Publish on the company wiki'. Then provide a brief summary of the full plan."
                workflow.logger.info(f"Running: {message}")
                result3 = await Runner.run(starting_agent=agent, input=message)

                return f"{result1.final_output}\n\n{result2.final_output}\n\n{result3.final_output}"
