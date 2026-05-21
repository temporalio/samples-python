import asyncio
import os
from datetime import timedelta
from typing import Optional

from agents import (
    Model,
    ModelProvider,
    OpenAIChatCompletionsModel,
    set_tracing_disabled,
)
from openai import AsyncOpenAI
from temporalio.client import Client
from temporalio.contrib.openai_agents import ModelActivityParameters, OpenAIAgentsPlugin
from temporalio.worker import Worker

from openai_agents.model_providers.workflows.tuning_engines_workflow import (
    TuningEnginesWorkflow,
)

TUNING_ENGINES_BASE_URL = os.environ.get(
    "TUNING_ENGINES_BASE_URL", "https://api.tuningengines.com/v1"
)
TUNING_ENGINES_MODEL = os.environ.get("TUNING_ENGINES_MODEL")
TUNING_ENGINES_API_KEY = os.environ.get("TUNING_ENGINES_API_KEY")

if not TUNING_ENGINES_API_KEY:
    raise RuntimeError("Set TUNING_ENGINES_API_KEY before starting this worker")

tuning_engines_client = AsyncOpenAI(
    base_url=TUNING_ENGINES_BASE_URL,
    api_key=TUNING_ENGINES_API_KEY,
)


class TuningEnginesModelProvider(ModelProvider):
    def get_model(self, model_name: Optional[str]) -> Model:
        model = OpenAIChatCompletionsModel(
            model=TUNING_ENGINES_MODEL or model_name or "tuning-engines-default",
            openai_client=tuning_engines_client,
        )
        return model


async def main():
    # Disable Agents SDK tracing — the default exporter sends traces to OpenAI's
    # backend, which requires an OpenAI API key not available in these samples.
    # Call here rather than in the workflow because it's a global side effect.
    set_tracing_disabled(disabled=True)

    client = await Client.connect(
        "localhost:7233",
        plugins=[
            OpenAIAgentsPlugin(
                model_params=ModelActivityParameters(
                    start_to_close_timeout=timedelta(seconds=30)
                ),
                model_provider=TuningEnginesModelProvider(),
            ),
        ],
    )

    worker = Worker(
        client,
        task_queue="openai-agents-model-providers-task-queue",
        workflows=[
            TuningEnginesWorkflow,
        ],
    )
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
