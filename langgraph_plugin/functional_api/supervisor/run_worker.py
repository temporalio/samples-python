"""Worker for the Supervisor Multi-Agent Functional API sample.

Prerequisites:
    - Temporal server running locally
    - OPENAI_API_KEY environment variable set
"""

import asyncio

from temporalio.client import Client
from temporalio.contrib.langgraph import LangGraphFunctionalPlugin
from temporalio.envconfig import ClientConfig
from temporalio.worker import Worker

from langgraph_plugin.functional_api.supervisor.entrypoint import supervisor_entrypoint
from langgraph_plugin.functional_api.supervisor.workflow import SupervisorWorkflow


async def main() -> None:
    plugin = LangGraphFunctionalPlugin(
        entrypoints={"supervisor_entrypoint": supervisor_entrypoint},
    )

    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")
    client = await Client.connect(**config, plugins=[plugin])

    worker = Worker(
        client,
        task_queue="langgraph-functional-supervisor",
        workflows=[SupervisorWorkflow],
    )

    print("Supervisor Multi-Agent worker started. Ctrl+C to exit.")
    print("Make sure OPENAI_API_KEY is set in your environment.")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
