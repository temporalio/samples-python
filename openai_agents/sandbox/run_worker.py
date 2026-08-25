from __future__ import annotations

import asyncio
from datetime import timedelta

from agents.sandbox.sandboxes.unix_local import UnixLocalSandboxClient
from temporalio.client import Client
from temporalio.contrib.openai_agents import (
    ModelActivityParameters,
    OpenAIAgentsPlugin,
    SandboxClientProvider,
)
from temporalio.worker import Worker

from openai_agents.sandbox.shared import SANDBOX_PROVIDER, TASK_QUEUE
from openai_agents.sandbox.workflows.local_sandbox_workflow import (
    LocalSandboxWorkflow,
)


async def main() -> None:
    # @@@SNIPSTART python-openai-agents-sandbox-worker
    client = await Client.connect(
        "localhost:7233",
        plugins=[
            OpenAIAgentsPlugin(
                model_params=ModelActivityParameters(
                    start_to_close_timeout=timedelta(seconds=60)
                ),
                # The plugin registers one set of sandbox activities per
                # provider, prefixed with the provider name. Register several
                # providers to let one worker serve several backends.
                sandbox_clients=[
                    SandboxClientProvider(SANDBOX_PROVIDER, UnixLocalSandboxClient()),
                ],
            ),
        ],
    )
    # @@@SNIPEND

    worker = Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[LocalSandboxWorkflow],
    )
    print("Worker started. Ctrl+C to exit.")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
