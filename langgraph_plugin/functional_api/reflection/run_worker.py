"""Worker for the Reflection Agent Functional API sample.

Starts a Temporal worker that can execute ReflectionWorkflow.

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

from langgraph_plugin.functional_api.reflection.entrypoint import reflection_entrypoint
from langgraph_plugin.functional_api.reflection.workflow import ReflectionWorkflow


async def main() -> None:
    plugin = LangGraphPlugin(
        graphs={"reflection_entrypoint": reflection_entrypoint},
        activity_options={
            "generate_content": activity_options(
                start_to_close_timeout=timedelta(minutes=2),
            ),
            "critique_content": activity_options(
                start_to_close_timeout=timedelta(minutes=2),
            ),
            "revise_content": activity_options(
                start_to_close_timeout=timedelta(minutes=2),
            ),
        },
    )

    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")
    client = await Client.connect(**config, plugins=[plugin])

    worker = Worker(
        client,
        task_queue="langgraph-functional-reflection",
        workflows=[ReflectionWorkflow],
    )

    print("Reflection Agent worker started. Ctrl+C to exit.")
    print("Make sure OPENAI_API_KEY is set in your environment.")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
