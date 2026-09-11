import asyncio

from temporalio.client import Client
from temporalio.contrib.openai_agents import OpenAIAgentsPlugin

from openai_agents.model_providers.workflows.openrouter_workflow import (
    OpenRouterAgentWorkflow,
)


async def main():
    client = await Client.connect(
        "localhost:7233",
        plugins=[
            OpenAIAgentsPlugin(),
        ],
    )

    result = await client.execute_workflow(
        OpenRouterAgentWorkflow.run,
        "What's the weather in Tokyo?",
        id="openai-agents-openrouter-workflow-id",
        task_queue="openai-agents-model-providers-task-queue",
    )
    print(f"Result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
