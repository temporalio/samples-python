import asyncio
import os
from datetime import timedelta

from agents.extensions.models.litellm_provider import LitellmProvider
from temporalio.client import Client
from temporalio.openai_agents import ModelActivityParameters, OpenAIAgentsPlugin
from temporalio.worker import Worker
from temporalio.worker.workflow_sandbox import (
    SandboxedWorkflowRunner,
    SandboxRestrictions,
)

from openai_agents.model_providers.workflows.litellm_auto_workflow import (
    LitellmAutoWorkflow,
)


async def main():
    # Disable tracing, including the provider installed by the plugin.
    os.environ["OPENAI_AGENTS_DISABLE_TRACING"] = "1"

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
        workflow_runner=SandboxedWorkflowRunner(
            restrictions=SandboxRestrictions.default.with_passthrough_modules("litellm")
        ),
        workflows=[
            LitellmAutoWorkflow,
        ],
    )
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
