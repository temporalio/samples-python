import asyncio

from temporalio.client import Client
from temporalio.contrib.openai_agents import OpenAIAgentsPlugin

from openai_agents.tools.workflows.file_search_workflow import FileSearchWorkflow


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
        FileSearchWorkflow.run,
        args=[
            "Be concise, and tell me 1 sentence about Arrakis I might not know.",
            "vs_68855c27140c8191849b5f1887d8d335",  # Vector store with Arrakis knowledge
        ],
        id="file-search-workflow",
        task_queue="openai-agents-tools-task-queue",
    )

    print(f"Result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
