"""Worker for Claude Agent workflows."""

from __future__ import annotations

import asyncio
from datetime import timedelta

from temporalio.client import Client
from temporalio.contrib.claude_agent import (
    ClaudeAgentPlugin,
    StatefulClaudeSessionProvider,
)
from temporalio.worker import Worker
from temporalio.workflow import ActivityConfig

from claude_agents.basic.activities.get_weather_activity import get_weather
from claude_agents.basic.workflows.hello_world_workflow import HelloWorldAgent
from claude_agents.basic.workflows.tools_workflow import ToolsWorkflow


async def main():
    """Run the worker with Claude Agent workflows."""
    # Create session providers for different sessions
    hello_session_provider = StatefulClaudeSessionProvider("hello-session")
    tools_session_provider = StatefulClaudeSessionProvider("tools-session")

    # Create client connected to server with Claude plugin
    client = await Client.connect(
        "localhost:7233",
        plugins=[
            ClaudeAgentPlugin(
                session_providers=[
                    hello_session_provider,
                    tools_session_provider,
                ],
            ),
        ],
    )

    # Create and run worker with workflows and activities
    worker = Worker(
        client,
        task_queue="claude-agents-basic-task-queue",
        workflows=[
            HelloWorldAgent,
            ToolsWorkflow,
        ],
        activities=[
            get_weather,
        ],
    )

    print("Starting Claude Agent worker...")
    print("Task queue: claude-agents-basic-task-queue")
    print("Available workflows:")
    print("  - HelloWorldAgent: Simple haiku responses")
    print("  - ToolsWorkflow: Weather tool demonstration")
    print("\nWorker is running. Press Ctrl+C to stop.")

    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())