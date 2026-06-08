"""Start the MCP workflow."""

import asyncio
import os

from temporalio.client import Client

from strands_plugin.mcp.workflow import MCPWorkflow


async def main() -> None:
    client = await Client.connect(os.environ.get("TEMPORAL_ADDRESS", "localhost:7233"))

    result = await client.execute_workflow(
        MCPWorkflow.run,
        "Use the echo tool to echo the message 'hello from MCP'.",
        id="strands-mcp",
        task_queue="strands-mcp",
    )

    print(f"Result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
