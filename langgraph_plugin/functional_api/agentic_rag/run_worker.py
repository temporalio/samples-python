"""Worker for the Agentic RAG Functional API sample.

Prerequisites:
    - Temporal server running locally
    - OPENAI_API_KEY environment variable set
"""

import asyncio
from datetime import timedelta

from temporalio.client import Client
from temporalio.contrib.langgraph import (
    LangGraphFunctionalPlugin,
    activity_options,
)
from temporalio.envconfig import ClientConfig
from temporalio.worker import Worker

from langgraph_plugin.functional_api.agentic_rag.entrypoint import (
    agentic_rag_entrypoint,
)
from langgraph_plugin.functional_api.agentic_rag.workflow import AgenticRagWorkflow


async def main() -> None:
    plugin = LangGraphFunctionalPlugin(
        entrypoints={"agentic_rag_entrypoint": agentic_rag_entrypoint},
        task_options={
            "retrieve_documents": activity_options(
                start_to_close_timeout=timedelta(minutes=1),
            ),
            "grade_documents": activity_options(
                start_to_close_timeout=timedelta(minutes=1),
            ),
            "rewrite_query": activity_options(
                start_to_close_timeout=timedelta(minutes=1),
            ),
            "generate_answer": activity_options(
                start_to_close_timeout=timedelta(minutes=2),
            ),
        },
    )

    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")
    client = await Client.connect(**config, plugins=[plugin])

    worker = Worker(
        client,
        task_queue="langgraph-functional-agentic-rag",
        workflows=[AgenticRagWorkflow],
    )

    print("Agentic RAG worker started. Ctrl+C to exit.")
    print("Make sure OPENAI_API_KEY is set in your environment.")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
