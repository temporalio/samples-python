import asyncio
import os

import logfire
from pydantic_ai.durable_exec.temporal import LogfirePlugin, PydanticAIPlugin
from temporalio.client import Client
from temporalio.worker import Worker

from pydantic_ai_plugin.logfire.workflow import ObservabilityWorkflow


async def main() -> None:
    if os.environ.get("LOGFIRE_TOKEN") is None:
        logfire.configure(send_to_logfire=False)
    client = await Client.connect(
        os.environ.get("TEMPORAL_ADDRESS", "localhost:7233"),
        plugins=[PydanticAIPlugin(), LogfirePlugin(metrics=False)],
    )
    await Worker(
        client,
        task_queue="pydantic-ai-logfire",
        workflows=[ObservabilityWorkflow],
    ).run()


if __name__ == "__main__":
    asyncio.run(main())
