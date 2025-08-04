import asyncio

from temporalio.client import Client
from temporalio.contrib.openai_agents import OpenAIAgentsPlugin

from openai_agents.basic.workflows.lifecycle_workflow import LifecycleWorkflow


async def main():
    client = await Client.connect(
        "localhost:7233",
        plugins=[
            OpenAIAgentsPlugin(),
        ],
    )

    user_input = input("Enter a max number: ")
    max_number = int(user_input)

    result = await client.execute_workflow(
        LifecycleWorkflow.run,
        max_number,
        id="lifecycle-workflow",
        task_queue="openai-agents-basic-task-queue",
    )

    print(f"Final result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
