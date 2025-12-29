"""Execute the Agentic RAG workflow."""

import asyncio

from temporalio.client import Client
from temporalio.envconfig import ClientConfig

from langgraph_samples.agentic_rag.workflow import AgenticRAGWorkflow


async def main() -> None:
    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")
    client = await Client.connect(**config)

    # This query requires retrieval from the knowledge base
    # The agent will:
    # 1. Decide to retrieve documents about the topic
    # 2. Grade the retrieved documents for relevance
    # 3. Generate an answer using the relevant documents
    result = await client.execute_workflow(
        AgenticRAGWorkflow.run,
        "What is the ReAct pattern and how does it work with Temporal?",
        id="agentic-rag-workflow",
        task_queue="langgraph-agentic-rag",
    )

    # Print only the text response
    print(result["messages"][-1]["content"])


if __name__ == "__main__":
    asyncio.run(main())
