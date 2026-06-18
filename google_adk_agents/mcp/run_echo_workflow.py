import asyncio

from temporalio.client import Client
from temporalio.contrib.google_adk_agents import GoogleAdkPlugin

from google_adk_agents.mcp.workflows.echo_workflow import EchoMcpWorkflow


async def main():
    client = await Client.connect("localhost:7233", plugins=[GoogleAdkPlugin()])

    result = await client.execute_workflow(
        EchoMcpWorkflow.run,
        "Echo 'hello from MCP'.",
        id="google-adk-agents-mcp-workflow-id",
        task_queue="google-adk-agents-mcp",
    )
    print(f"Result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
