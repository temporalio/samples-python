from __future__ import annotations

from agents import Agent, Runner, trace
from temporalio import workflow
from temporalio.contrib import openai_agents as temporal_openai_agents


@workflow.defn
class FileSystemWorkflow:
    @workflow.run
    async def run(self) -> str:
        async with temporal_openai_agents.workflow.stateful_mcp_server(
            "FileSystemServer",
        ) as server:
            with trace(workflow_name="MCP File System Example"):
                agent = Agent(
                    name="Assistant",
                    instructions="Use the tools to read the filesystem and answer questions based on those files.",
                    mcp_servers=[server],
                )

                # List the files it can read
                message = "Read the files and list them."
                print(f"Running: {message}")
                result1 = await Runner.run(starting_agent=agent, input=message)

                # Ask about books
                message = "What is my #1 favorite book?"
                print(f"\n\nRunning: {message}")
                result2 = await Runner.run(starting_agent=agent, input=message)

                # Ask a question that reads then reasons.
                message = (
                    "Look at my favorite songs. Suggest one new song that I might like."
                )
                print(f"\n\nRunning: {message}")
                result3 = await Runner.run(starting_agent=agent, input=message)

                return f"{result1.final_output}\n\n{result2.final_output}\n\n{result3.final_output}"
