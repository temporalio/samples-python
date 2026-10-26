"""Start one Workflow per model name; they run concurrently on the same Worker."""

import argparse
import asyncio
import os

from temporalio.client import Client, WorkflowFailureError
from temporalio.exceptions import FailureError
from temporalio.openai_agents import OpenAIAgentsPlugin

from openai_agents.model_providers.openai_compatible_providers import PROVIDERS
from openai_agents.model_providers.workflows.openai_compatible_workflow import (
    OpenAICompatibleAgentInput,
    OpenAICompatibleAgentWorkflow,
)


async def run_one(client: Client, model: str) -> None:
    try:
        result = await client.execute_workflow(
            OpenAICompatibleAgentWorkflow.run,
            OpenAICompatibleAgentInput(
                prompt="What's the weather in Tokyo?", model=model
            ),
            id=f"openai-agents-openai-compatible-{model.replace('/', '-')}",
            task_queue="openai-agents-model-providers-task-queue",
        )
        print(f"{model}:\n{result}\n")
    except WorkflowFailureError as e:
        # Report the root cause, such as the provider's "Set FIREWORKS_API_KEY".
        cause = e.cause
        while isinstance(cause, FailureError) and cause.cause is not None:
            cause = cause.cause
        print(f"{model}: failed: {cause}\n")


async def main(models: list[str]) -> None:
    client = await Client.connect(
        "localhost:7233",
        plugins=[
            OpenAIAgentsPlugin(),
        ],
    )
    # Each Workflow names its own model, so these run side by side on one
    # Worker, each on its own provider.
    await asyncio.gather(*(run_one(client, model) for model in models))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--model",
        action="append",
        dest="models",
        metavar="PROVIDER/MODEL",
        help="model to run, such as together/openai/gpt-oss-120b; repeat for "
        "several. Defaults to each provider whose API key is set in this shell.",
    )
    args = parser.parse_args()
    models = args.models or [
        f"{provider.name}/{provider.default_model}"
        for provider in PROVIDERS.values()
        if os.environ.get(provider.api_key_env)
    ]
    if not models:
        parser.error("pass --model or export a provider API key")
    asyncio.run(main(models))
