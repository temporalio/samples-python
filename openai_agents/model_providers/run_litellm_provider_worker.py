import asyncio
from datetime import timedelta

from agents.extensions.models.litellm_provider import LitellmProvider
from temporalio.client import Client
from temporalio.contrib.openai_agents import ModelActivityParameters, OpenAIAgentsPlugin
from temporalio.worker import Worker

from openai_agents.model_providers.workflows.litellm_auto_workflow import (
    LitellmAutoWorkflow,
)


async def main():
    # Create client connected to server at the given address
    client = await Client.connect(
        "localhost:7233",
        plugins=[
            OpenAIAgentsPlugin(
                model_params=ModelActivityParameters(
                    start_to_close_timeout=timedelta(seconds=30)
                ),
                model_provider=LitellmProvider(),
            ),
        ],
    )

    worker = Worker(
        client,
        task_queue="openai-agents-model-providers-task-queue",
        workflows=[
            LitellmAutoWorkflow,
        ],
    )
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
