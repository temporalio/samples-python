import asyncio

from temporalio.client import Client

from mcp_sequential_thinking.agent_workflow import AgentWorkflow


async def main():
    client = await Client.connect("localhost:7233")
    await client.execute_workflow(
        AgentWorkflow.run,
        id="my-workflow-id",
        task_queue="mcp-sequential-thinking-task-queue",
    )


if __name__ == "__main__":
    asyncio.run(main())
