"""Start the durable MCP workflow for a selected transport."""

import argparse
import asyncio
from typing import cast
from uuid import uuid4

from temporalio.client import Client
from temporalio.envconfig import ClientConfig

from workflow import TRANSPORTS, MCPDemoWorkflow, Transport, task_queue


async def main(transport: Transport) -> None:
    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")
    client = await Client.connect(**config)

    result = await client.execute_workflow(
        MCPDemoWorkflow.run,
        transport,
        id=f"temporal-mcp-{transport}-{uuid4()}",
        task_queue=task_queue(transport),
    )
    print(result)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("transport", choices=TRANSPORTS)
    args = parser.parse_args()
    asyncio.run(main(cast(Transport, args.transport)))
