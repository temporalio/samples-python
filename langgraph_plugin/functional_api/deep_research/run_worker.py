"""Worker for the Deep Research Functional API sample.

Prerequisites:
    - Temporal server running locally
    - OPENAI_API_KEY environment variable set
"""

import asyncio

from temporalio.client import Client
from temporalio.contrib.langgraph import LangGraphFunctionalPlugin
from temporalio.envconfig import ClientConfig
from temporalio.worker import Worker

from langgraph_plugin.functional_api.deep_research.entrypoint import (
    deep_research_entrypoint,
)
from langgraph_plugin.functional_api.deep_research.workflow import DeepResearchWorkflow


async def main() -> None:
    plugin = LangGraphFunctionalPlugin(
        entrypoints={"deep_research_entrypoint": deep_research_entrypoint},
    )

    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")
    client = await Client.connect(**config, plugins=[plugin])

    worker = Worker(
        client,
        task_queue="langgraph-functional-deep-research",
        workflows=[DeepResearchWorkflow],
    )

    print("Deep Research worker started. Ctrl+C to exit.")
    print("Make sure OPENAI_API_KEY is set in your environment.")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
