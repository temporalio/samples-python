import asyncio
import logging
import os
from datetime import timedelta

from agents import OpenAIProvider, set_tracing_disabled
from openai import AsyncOpenAI
from temporalio.client import Client
from temporalio.contrib.openai_agents import ModelActivityParameters, OpenAIAgentsPlugin
from temporalio.worker import Worker

from openai_agents.model_providers.workflows.openrouter_workflow import (
    OpenRouterAgentWorkflow,
)


# @@@SNIPSTART python-openai-agents-openrouter-provider
def openrouter_provider() -> OpenAIProvider:
    """OpenAI Agents SDK model provider backed by OpenRouter.

    OpenRouter speaks the OpenAI Chat Completions API, so the stock provider
    works once it is pointed at OpenRouter's base URL. Client retries are off:
    the plugin runs each model call as a Temporal Activity, and Temporal owns
    the retries.
    """
    default_headers: dict[str, str] = {}
    # Optional app attribution for OpenRouter's rankings.
    if referer := os.getenv("OPENROUTER_HTTP_REFERER"):
        default_headers["HTTP-Referer"] = referer
    if title := os.getenv("OPENROUTER_APP_TITLE"):
        default_headers["X-OpenRouter-Title"] = title

    client = AsyncOpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.environ["OPENROUTER_API_KEY"],
        max_retries=0,
        default_headers=default_headers or None,
    )
    # Chat Completions is OpenRouter's primary endpoint; the Agents SDK
    # defaults to the Responses API, which OpenRouter offers only in beta.
    return OpenAIProvider(openai_client=client, use_responses=False)


# @@@SNIPEND


async def main():
    # Disable Agents SDK tracing: the default exporter sends traces to OpenAI's
    # backend, which needs an OpenAI API key that this sample does not have.
    set_tracing_disabled(disabled=True)

    logging.basicConfig(level=logging.WARNING)
    logging.getLogger("temporalio.workflow").setLevel(logging.DEBUG)

    client = await Client.connect(
        "localhost:7233",
        plugins=[
            OpenAIAgentsPlugin(
                model_params=ModelActivityParameters(
                    start_to_close_timeout=timedelta(seconds=60)
                ),
                model_provider=openrouter_provider(),
            ),
        ],
    )

    worker = Worker(
        client,
        task_queue="openai-agents-model-providers-task-queue",
        workflows=[
            OpenRouterAgentWorkflow,
        ],
    )
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
