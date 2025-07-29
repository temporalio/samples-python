import asyncio

from temporalio.client import Client
from temporalio.contrib.openai_agents import OpenAIAgentsPlugin

from openai_agents.tools.workflows.code_interpreter_workflow import (
    CodeInterpreterWorkflow,
)


async def main():
    # Create client connected to server at the given address
    client = await Client.connect(
        "localhost:7233",
        plugins=[
            OpenAIAgentsPlugin(),
        ],
    )

    # Execute a workflow
    result = await client.execute_workflow(
        CodeInterpreterWorkflow.run,
        "What is the square root of 273 * 312821 plus 1782?",
        id="code-interpreter-workflow",
        task_queue="openai-agents-tools-task-queue",
    )

    print(f"Result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
