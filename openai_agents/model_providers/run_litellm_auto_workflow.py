import asyncio

from temporalio.client import Client
from temporalio.contrib.openai_agents import OpenAIAgentsPlugin

from openai_agents.model_providers.workflows.litellm_auto_workflow import LitellmAutoWorkflow


async def main():
    client = await Client.connect(
        "localhost:7233",
        plugins=[
            OpenAIAgentsPlugin(),
        ],
    )

    result = await client.execute_workflow(
        LitellmAutoWorkflow.run,
        "What's the weather in Tokyo?",
        id="litellm-auto-workflow-id",
        task_queue="openai-agents-model-providers-task-queue",
    )
    print(f"Result: {result}")


if __name__ == "__main__":
    asyncio.run(main())