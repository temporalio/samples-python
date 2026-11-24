"""Worker that serves Baseten, Fireworks AI, and Together AI from one process."""

import asyncio
import logging
import os
import sys
from datetime import timedelta

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


async def main() -> None:
    # Disable tracing, including the provider installed by the plugin.
    os.environ["OPENAI_AGENTS_DISABLE_TRACING"] = "1"

    logging.basicConfig(level=logging.WARNING)
    logging.getLogger("temporalio.workflow").setLevel(logging.DEBUG)

    # @@@SNIPSTART python-openai-agents-openai-compatible-worker
    # One provider for every endpoint whose API key is set. The model name on
    # each Workflow's agent selects the endpoint.
    model_provider = OpenAICompatibleModelProvider(PROVIDERS.values())
    if not model_provider.configured:
        env_vars = ", ".join(provider.api_key_env for provider in PROVIDERS.values())
        sys.exit(f"No provider API key is set; export at least one of {env_vars}.")
    print(f"Serving providers: {', '.join(model_provider.configured)}", flush=True)

    client = await Client.connect(
        "localhost:7233",
        plugins=[
            OpenAIAgentsPlugin(
                model_params=ModelActivityParameters(
                    # Model calls time out after 60 seconds by default. Raise
                    # this for slow models or deployments that scale up from
                    # zero.
                    start_to_close_timeout=timedelta(seconds=60),
                    # The plugin heartbeats, so a Worker that dies mid-call is
                    # noticed in seconds rather than after the full timeout.
                    heartbeat_timeout=timedelta(seconds=10),
                ),
                model_provider=model_provider,
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
    asyncio.run(main())
