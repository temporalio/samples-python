"""Run the HelloWorldAgent workflow."""

import asyncio

from temporalio.client import Client
from temporalio.contrib.claude_agent import (
    ClaudeAgentPlugin,
    StatefulClaudeSessionProvider,
)

from claude_agents.basic.workflows.hello_world_workflow import HelloWorldAgent


async def main():
    """Run the hello world workflow with Claude."""
    # Create session provider for the hello world session
    session_provider = StatefulClaudeSessionProvider("hello-session")

    # Create client connected to server with Claude plugin
    client = await Client.connect(
        "localhost:7233",
        plugins=[
            ClaudeAgentPlugin(
                session_providers=[session_provider],
            ),
        ],
    )

    # Execute the workflow
    result = await client.execute_workflow(
        HelloWorldAgent.run,
        "Tell me about recursion in programming.",
        id="claude-hello-world-workflow",
        task_queue="claude-agents-basic-task-queue",
    )

    print(f"Claude responded with this haiku:\n{result}")


if __name__ == "__main__":
    asyncio.run(main())