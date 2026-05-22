import asyncio

from temporalio.client import Client
from temporalio.contrib.openai_agents import OpenAIAgentsPlugin

from openai_agents.model_providers.workflows.tuning_engines_workflow import (
    TuningEnginesWorkflow,
)


async def main():
    client = await Client.connect(
        "localhost:7233",
        plugins=[
            OpenAIAgentsPlugin(),
        ],
    )

    result = await client.execute_workflow(
        TuningEnginesWorkflow.run,
        "Explain why a governed model gateway is useful in production.",
        id="tuning-engines-workflow-id",
        task_queue="openai-agents-model-providers-task-queue",
    )
    print(f"Result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
