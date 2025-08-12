import asyncio
import logging
from datetime import timedelta
from typing import Optional

from agents import Model, ModelProvider, OpenAIChatCompletionsModel
from openai import AsyncOpenAI
from temporalio.client import Client
from temporalio.contrib.openai_agents import ModelActivityParameters, OpenAIAgentsPlugin
from temporalio.worker import Worker

from openai_agents.model_providers.workflows.gpt_oss_workflow import GptOssWorkflow

ollama_client = AsyncOpenAI(
    base_url="http://localhost:11434/v1",  # Local Ollama API endpoint
    api_key="ollama",  # Ignored by Ollama
)


class CustomModelProvider(ModelProvider):
    def get_model(self, model_name: Optional[str]) -> Model:
        model = OpenAIChatCompletionsModel(
            model=model_name if model_name else "gpt-oss:20b",
            openai_client=ollama_client,
        )
        return model


async def main():
    # Configure logging to show workflow debug messages
    logging.basicConfig(level=logging.WARNING)
    logging.getLogger("temporalio.workflow").setLevel(logging.DEBUG)

    # Create client connected to server at the given address
    client = await Client.connect(
        "localhost:7233",
        plugins=[
            OpenAIAgentsPlugin(
                model_params=ModelActivityParameters(
                    start_to_close_timeout=timedelta(seconds=30)
                ),
                model_provider=CustomModelProvider(),
            ),
        ],
    )

    worker = Worker(
        client,
        task_queue="openai-agents-model-providers-task-queue",
        workflows=[
            GptOssWorkflow,
        ],
    )
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
