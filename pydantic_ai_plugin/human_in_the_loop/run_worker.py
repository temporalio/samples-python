import asyncio
import os

from pydantic_ai.durable_exec.temporal import PydanticAIPlugin
from temporalio.client import Client
from temporalio.worker import Worker

from pydantic_ai_plugin.human_in_the_loop.workflow import ApprovalWorkflow


async def main() -> None:
    client = await Client.connect(
        os.environ.get("TEMPORAL_ADDRESS", "localhost:7233"),
        plugins=[PydanticAIPlugin()],
    )
    await Worker(
        client,
        task_queue="pydantic-ai-approval",
        workflows=[ApprovalWorkflow],
    ).run()


if __name__ == "__main__":
    asyncio.run(main())
