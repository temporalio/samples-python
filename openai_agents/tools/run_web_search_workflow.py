import asyncio

from temporalio.client import Client
from temporalio.contrib.openai_agents import OpenAIAgentsPlugin

from openai_agents.tools.workflows.web_search_workflow import WebSearchWorkflow


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
        WebSearchWorkflow.run,
        args=[
            "search the web for 'local sports news' and give me 1 interesting update in a sentence.",
            "New York",
        ],
        id="web-search-workflow",
        task_queue="openai-agents-tools-task-queue",
    )

    print(f"Result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
