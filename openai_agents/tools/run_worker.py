from __future__ import annotations

import asyncio
from datetime import timedelta

from temporalio.client import Client
from temporalio.contrib.openai_agents import ModelActivityParameters, OpenAIAgentsPlugin
from temporalio.worker import Worker

from openai_agents.tools.workflows.code_interpreter_workflow import (
    CodeInterpreterWorkflow,
)
from openai_agents.tools.workflows.file_search_workflow import FileSearchWorkflow
from openai_agents.tools.workflows.image_generator_workflow import (
    ImageGeneratorWorkflow,
)
from openai_agents.tools.workflows.web_search_workflow import WebSearchWorkflow


async def main():
    # Create client connected to server at the given address
    client = await Client.connect(
        "localhost:7233",
        plugins=[
            OpenAIAgentsPlugin(
                model_params=ModelActivityParameters(
                    start_to_close_timeout=timedelta(seconds=60)
                )
            ),
        ],
    )

    worker = Worker(
        client,
        task_queue="openai-agents-tools-task-queue",
        workflows=[
            CodeInterpreterWorkflow,
            FileSearchWorkflow,
            ImageGeneratorWorkflow,
            WebSearchWorkflow,
        ],
        activities=[
            # No custom activities needed for these workflows
        ],
    )
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
