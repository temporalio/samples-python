import asyncio
import os

from temporalio.client import Client
from temporalio.worker import Worker

from pydantic_ai.durable_exec.temporal import PydanticAIPlugin
from pydantic_ai_plugin.structured_output.workflow import StructuredOutputWorkflow


async def main() -> None:
    client = await Client.connect(
        os.environ.get("TEMPORAL_ADDRESS", "localhost:7233"),
        plugins=[PydanticAIPlugin()],
    )
    await Worker(
        client,
        task_queue="pydantic-ai-structured-output",
        workflows=[StructuredOutputWorkflow],
    ).run()


if __name__ == "__main__":
    asyncio.run(main())
