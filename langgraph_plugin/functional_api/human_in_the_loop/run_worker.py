"""Worker for the Human-in-the-Loop Functional API sample.

Prerequisites:
    - Temporal server running locally
"""

import asyncio

from temporalio.client import Client
from temporalio.contrib.langgraph import LangGraphFunctionalPlugin
from temporalio.envconfig import ClientConfig
from temporalio.worker import Worker

from langgraph_plugin.functional_api.human_in_the_loop.entrypoint import (
    approval_entrypoint,
)
from langgraph_plugin.functional_api.human_in_the_loop.workflow import ApprovalWorkflow


async def main() -> None:
    plugin = LangGraphFunctionalPlugin(
        entrypoints={"approval_entrypoint": approval_entrypoint},
    )

    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")
    client = await Client.connect(**config, plugins=[plugin])

    worker = Worker(
        client,
        task_queue="langgraph-functional-approval",
        workflows=[ApprovalWorkflow],
    )

    print("Human-in-the-Loop worker started. Ctrl+C to exit.")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
