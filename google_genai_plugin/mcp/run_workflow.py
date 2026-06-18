"""Start the MCP workflow."""

# @@@SNIPSTART python-google-genai-mcp-run-workflow
import asyncio
import os

from temporalio.client import Client

from google_genai_plugin.mcp.workflow import McpWorkflow


async def main() -> None:
    client = await Client.connect(os.environ.get("TEMPORAL_ADDRESS", "localhost:7233"))

    result = await client.execute_workflow(
        McpWorkflow.run,
        "Use the echo tool to echo back the phrase: durable execution.",
        id="google-genai-mcp",
        task_queue="google-genai-mcp",
    )

    print(f"Result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
# @@@SNIPEND
