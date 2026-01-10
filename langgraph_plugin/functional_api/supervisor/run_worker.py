"""Worker for the Supervisor Multi-Agent Functional API sample.

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

from langgraph_plugin.functional_api.supervisor.entrypoint import supervisor_entrypoint
from langgraph_plugin.functional_api.supervisor.workflow import SupervisorWorkflow


async def main() -> None:
    plugin = LangGraphPlugin(
        graphs={"supervisor_entrypoint": supervisor_entrypoint},
        activity_options={
            "supervisor_decide": activity_options(
                start_to_close_timeout=timedelta(minutes=1),
            ),
            "researcher_work": activity_options(
                start_to_close_timeout=timedelta(minutes=3),
            ),
            "writer_work": activity_options(
                start_to_close_timeout=timedelta(minutes=3),
            ),
            "analyst_work": activity_options(
                start_to_close_timeout=timedelta(minutes=2),
            ),
        },
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
