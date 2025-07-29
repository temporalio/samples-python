import asyncio

from temporalio.client import Client
from temporalio.contrib.openai_agents import OpenAIAgentsPlugin

from openai_agents.basic.workflows.previous_response_id_workflow import (
    PreviousResponseIdWorkflow,
)


async def main():
    client = await Client.connect(
        "localhost:7233",
        plugins=[
            OpenAIAgentsPlugin(),
        ],
    )

    first_question = "What is the largest country in South America?"
    follow_up_question = "What is the capital of that country?"

    result = await client.execute_workflow(
        PreviousResponseIdWorkflow.run,
        args=[first_question, follow_up_question],
        id="previous-response-id-workflow",
        task_queue="openai-agents-basic-task-queue",
    )

    print("\nFinal results:")
    print(f"1. {result[0]}")
    print(f"2. {result[1]}")


if __name__ == "__main__":
    asyncio.run(main())
