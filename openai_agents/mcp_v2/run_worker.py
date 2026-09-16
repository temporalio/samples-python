from __future__ import annotations

import asyncio
import logging
from datetime import timedelta

from agents.mcp import MCPServerStreamableHttp
from temporalio.client import Client
from temporalio.envconfig import ClientConfig
from temporalio.openai_agents import ModelActivityParameters, OpenAIAgentsPlugin
from temporalio.worker import Worker
from workflow import (
    MCP_SERVER_NAME,
    TASK_QUEUE,
    StreamableHttpV2Workflow,
)


def streamable_http_server() -> MCPServerStreamableHttp:
    return MCPServerStreamableHttp(
        name=MCP_SERVER_NAME,
        params={"url": "http://localhost:8000/mcp"},
    )


async def main() -> None:
    logging.basicConfig(level=logging.INFO)

    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")
    client = await Client.connect(
        **config,
        plugins=[
            OpenAIAgentsPlugin(
                model_params=ModelActivityParameters(
                    start_to_close_timeout=timedelta(seconds=60)
                ),
                mcp_servers={MCP_SERVER_NAME: streamable_http_server},
            ),
        ],
    )

    worker = Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[StreamableHttpV2Workflow],
    )
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
