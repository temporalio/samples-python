import asyncio

from temporalio.client import Client
from temporalio.openai_agents import OpenAIAgentsPlugin

from openai_agents.model_providers.workflows.openai_compatible_workflow import (
    OpenAICompatibleAgentWorkflow,
)


async def main() -> None:
    client = await Client.connect(
        "localhost:7233",
        plugins=[
            OpenAIAgentsPlugin(),
        ],
    )

    result = await client.execute_workflow(
        OpenAICompatibleAgentWorkflow.run,
        "What's the weather in Tokyo?",
        id="openai-agents-openai-compatible-workflow-id",
        task_queue="openai-agents-model-providers-task-queue",
    )
    print(f"Result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
