"""Worker for the Plan-and-Execute Functional API sample.

Prerequisites:
    - Temporal server running locally
    - OPENAI_API_KEY environment variable set
"""

import asyncio
from datetime import timedelta

from temporalio.client import Client
from temporalio.contrib.langgraph import (
    LangGraphPlugin,
    activity_options,
)
from temporalio.envconfig import ClientConfig
from temporalio.worker import Worker

from langgraph_plugin.functional_api.plan_and_execute.entrypoint import (
    plan_execute_entrypoint,
)
from langgraph_plugin.functional_api.plan_and_execute.workflow import (
    PlanExecuteWorkflow,
)


async def main() -> None:
    plugin = LangGraphPlugin(
        graphs={"plan_execute_entrypoint": plan_execute_entrypoint},
        activity_options={
            "create_plan": activity_options(
                start_to_close_timeout=timedelta(minutes=2),
            ),
            "execute_step": activity_options(
                start_to_close_timeout=timedelta(minutes=2),
            ),
            "generate_response": activity_options(
                start_to_close_timeout=timedelta(minutes=1),
            ),
        },
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
