import asyncio

from temporalio.client import Client
from temporalio.contrib.openai_agents import OpenAIAgentsPlugin

from openai_agents.hosted_mcp.workflows.approval_mcp_workflow import ApprovalMCPWorkflow


async def main():
    # Create client connected to server at the given address
    client = await Client.connect(
        "localhost:7233",
        plugins=[
            OpenAIAgentsPlugin(),
        ],
    )

    # Execute a workflow
    result = await client.execute_workflow(
        ApprovalMCPWorkflow.run,
        "Which language is this repo written in?",
        id="approval-mcp-workflow",
        task_queue="openai-agents-hosted-mcp-task-queue",
    )

    print(f"Result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
