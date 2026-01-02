"""Execute the Agentic RAG Functional API workflow."""

import asyncio

from temporalio.client import Client
from temporalio.envconfig import ClientConfig

from langgraph_plugin.functional_api.agentic_rag.workflow import AgenticRagWorkflow


async def main() -> None:
    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")
    client = await Client.connect(**config)

    question = "What is LangGraph and how does it work with Temporal?"

    result = await client.execute_workflow(
        AgenticRagWorkflow.run,
        question,
        id="agentic-rag-functional-workflow",
        task_queue="langgraph-functional-agentic-rag",
    )

    print(f"Question: {result.get('question')}")
    print(f"Status: {result.get('status')}")
    print(f"Query Rewrites: {result.get('query_rewrites')}")
    print(f"Documents Used: {result.get('documents_used')}")
    print(f"\nAnswer:\n{result.get('answer')}")


if __name__ == "__main__":
    asyncio.run(main())
