"""Worker that runs the agent on Baseten, Fireworks AI, or Together AI."""

import argparse
import asyncio
import logging
from datetime import timedelta

from agents import set_tracing_disabled
from temporalio.client import Client
from temporalio.openai_agents import ModelActivityParameters, OpenAIAgentsPlugin
from temporalio.worker import Worker

from openai_agents.model_providers.openai_compatible_providers import (
    PROVIDERS,
    OpenAICompatibleModelProvider,
)
from openai_agents.model_providers.workflows.openai_compatible_workflow import (
    OpenAICompatibleAgentWorkflow,
)


async def main(provider_name: str) -> None:
    # Disable Agents SDK tracing: the default exporter sends traces to OpenAI's
    # backend, which needs an OpenAI API key that this sample does not have.
    set_tracing_disabled(disabled=True)

    logging.basicConfig(level=logging.WARNING)
    logging.getLogger("temporalio.workflow").setLevel(logging.DEBUG)

    # @@@SNIPSTART python-openai-agents-openai-compatible-worker
    client = await Client.connect(
        "localhost:7233",
        plugins=[
            OpenAIAgentsPlugin(
                model_params=ModelActivityParameters(
                    # A custom model provider must set a timeout. Raise it for
                    # slow models or deployments that scale up from zero.
                    start_to_close_timeout=timedelta(seconds=60),
                    # The plugin heartbeats, so a Worker that dies mid-call is
                    # noticed in seconds rather than after the full timeout.
                    heartbeat_timeout=timedelta(seconds=10),
                ),
                model_provider=OpenAICompatibleModelProvider(PROVIDERS[provider_name]),
            ),
        ],
    )

    worker = Worker(
        client,
        task_queue="openai-agents-model-providers-task-queue",
        workflows=[OpenAICompatibleAgentWorkflow],
    )
    await worker.run()
    # @@@SNIPEND


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--provider",
        choices=sorted(PROVIDERS),
        required=True,
        help="which provider serves the model",
    )
    args = parser.parse_args()
    asyncio.run(main(args.provider))
