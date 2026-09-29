from __future__ import annotations

import asyncio

from temporalio.client import Client
from temporalio.envconfig import ClientConfig
from temporalio.openai_agents import OpenAIAgentsPlugin

from workflow import TASK_QUEUE, StreamableHttpV2Workflow


async def main() -> None:
    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")
    client = await Client.connect(
        **config,
        plugins=[OpenAIAgentsPlugin()],
    )

    result = await client.execute_workflow(
        StreamableHttpV2Workflow.run,
        id="streamable-http-v2-workflow",
        task_queue=TASK_QUEUE,
    )
    print(f"Result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
