import asyncio

from temporalio.client import Client
from temporalio.contrib.openai_agents import OpenAIAgentsPlugin

from openai_agents.agent_patterns.workflows.forcing_tool_use_workflow import (
    ForcingToolUseWorkflow,
)


async def main():
    # Create client connected to server at the given address
    client = await Client.connect(
        "localhost:7233",
        plugins=[
            OpenAIAgentsPlugin(),
        ],
    )

    # Execute workflows with different tool use behaviors
    print("Testing default behavior:")
    result1 = await client.execute_workflow(
        ForcingToolUseWorkflow.run,
        "default",
        id="forcing-tool-use-workflow-default",
        task_queue="openai-agents-patterns-task-queue",
    )
    print(f"Default result: {result1}")

    print("\nTesting first_tool behavior:")
    result2 = await client.execute_workflow(
        ForcingToolUseWorkflow.run,
        "first_tool",
        id="forcing-tool-use-workflow-first-tool",
        task_queue="openai-agents-patterns-task-queue",
    )
    print(f"First tool result: {result2}")

    print("\nTesting custom behavior:")
    result3 = await client.execute_workflow(
        ForcingToolUseWorkflow.run,
        "custom",
        id="forcing-tool-use-workflow-custom",
        task_queue="openai-agents-patterns-task-queue",
    )
    print(f"Custom result: {result3}")


if __name__ == "__main__":
    asyncio.run(main())
