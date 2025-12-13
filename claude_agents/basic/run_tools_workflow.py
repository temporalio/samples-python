"""Run the ToolsWorkflow with weather tool support."""

import asyncio

from temporalio.client import Client
from temporalio.contrib.claude_agent import (
    ClaudeAgentPlugin,
    StatefulClaudeSessionProvider,
)

from claude_agents.basic.workflows.tools_workflow import ToolsWorkflow


async def main():
    """Run the tools workflow with Claude."""
    # Create session provider for the tools session
    session_provider = StatefulClaudeSessionProvider("tools-session")

    # Create client connected to server with Claude plugin
    client = await Client.connect(
        "localhost:7233",
        plugins=[
            ClaudeAgentPlugin(
                session_providers=[session_provider],
            ),
        ],
    )

    # Execute the workflow with a weather question
    result = await client.execute_workflow(
        ToolsWorkflow.run,
        "What's the weather like in San Francisco?",
        id="claude-tools-workflow",
        task_queue="claude-agents-basic-task-queue",
    )

    print(f"Claude's response:\n{result}")


if __name__ == "__main__":
    asyncio.run(main())