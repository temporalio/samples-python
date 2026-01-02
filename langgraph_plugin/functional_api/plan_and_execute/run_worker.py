"""Worker for the Plan-and-Execute Functional API sample.

Prerequisites:
    - Temporal server running locally
    - OPENAI_API_KEY environment variable set
"""

import asyncio

from temporalio.client import Client
from temporalio.contrib.langgraph import LangGraphFunctionalPlugin
from temporalio.envconfig import ClientConfig
from temporalio.worker import Worker

from langgraph_plugin.functional_api.plan_and_execute.entrypoint import (
    plan_execute_entrypoint,
)
from langgraph_plugin.functional_api.plan_and_execute.workflow import (
    PlanExecuteWorkflow,
)


async def main() -> None:
    plugin = LangGraphFunctionalPlugin(
        entrypoints={"plan_execute_entrypoint": plan_execute_entrypoint},
    )

    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")
    client = await Client.connect(**config, plugins=[plugin])

    worker = Worker(
        client,
        task_queue="langgraph-functional-plan-execute",
        workflows=[PlanExecuteWorkflow],
    )

    print("Plan-and-Execute worker started. Ctrl+C to exit.")
    print("Make sure OPENAI_API_KEY is set in your environment.")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
