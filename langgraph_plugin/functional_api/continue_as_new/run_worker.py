"""Worker for the Continue-as-New LangGraph Functional API example.

Starts a Temporal worker that can execute ContinueAsNewWorkflow.
"""

import asyncio
import logging
from datetime import timedelta

from temporalio.client import Client
from temporalio.contrib.langgraph import (
    LangGraphPlugin,
    activity_options,
)
from temporalio.envconfig import ClientConfig
from temporalio.worker import Worker

from langgraph_plugin.functional_api.continue_as_new.entrypoint import (
    pipeline_entrypoint,
)
from langgraph_plugin.functional_api.continue_as_new.workflow import (
    ContinueAsNewWorkflow,
)

# Configure logging to see task execution
logging.basicConfig(level=logging.INFO)


async def main() -> None:
    # Create the plugin with our entrypoint registered
    plugin = LangGraphPlugin(
        graphs={"pipeline_entrypoint": pipeline_entrypoint},
        default_activity_options=activity_options(
            start_to_close_timeout=timedelta(seconds=30),
        ),
    )

    # Connect to Temporal with the plugin
    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")
    client = await Client.connect(**config, plugins=[plugin])

    # Create and run the worker
    worker = Worker(
        client,
        task_queue="langgraph-functional-continue-as-new",
        workflows=[ContinueAsNewWorkflow],
    )

    print("Worker started. Ctrl+C to exit.")
    print("Task execution will be logged - watch for cache hits!")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
