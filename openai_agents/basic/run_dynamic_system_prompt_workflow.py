import asyncio

from temporalio.client import Client
from temporalio.contrib.openai_agents import OpenAIAgentsPlugin

from openai_agents.basic.workflows.dynamic_system_prompt_workflow import (
    DynamicSystemPromptWorkflow,
)


async def main():
    client = await Client.connect(
        "localhost:7233",
        plugins=[
            OpenAIAgentsPlugin(),
        ],
    )

    user_message = "Tell me a joke."

    result = await client.execute_workflow(
        DynamicSystemPromptWorkflow.run,
        user_message,
        id="dynamic-prompt-workflow",
        task_queue="openai-agents-basic-task-queue",
    )
    print(result)
    print()

    # Run with specific style
    result = await client.execute_workflow(
        DynamicSystemPromptWorkflow.run,
        args=[user_message, "pirate"],
        id="dynamic-prompt-pirate-workflow",
        task_queue="openai-agents-basic-task-queue",
    )
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
