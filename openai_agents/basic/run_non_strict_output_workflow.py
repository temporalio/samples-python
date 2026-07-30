import asyncio

from temporalio.client import Client
from temporalio.contrib.openai_agents import OpenAIAgentsPlugin

from openai_agents.basic.workflows.non_strict_output_workflow import (
    NonStrictOutputWorkflow,
)


async def main():
    client = await Client.connect(
        "localhost:7233",
        plugins=[
            OpenAIAgentsPlugin(),
        ],
    )

    input_message = "Tell me 3 short jokes."

    result = await client.execute_workflow(
        NonStrictOutputWorkflow.run,
        input_message,
        id="non-strict-output-workflow",
        task_queue="openai-agents-basic-task-queue",
    )

    print("=== Non-Strict Output Type Results ===")
    for key, value in result.items():
        print(f"{key}: {value}")
        print()


if __name__ == "__main__":
    asyncio.run(main())
