import asyncio

from temporalio.client import Client
from temporalio.common import WorkflowIDReusePolicy

from openai_agents.workflows.tools_workflow import ToolsWorkflow


async def main():
    # Create client connected to server at the given address
    client = await Client.connect("localhost:7233")

    # Execute a workflow
    result = await client.execute_workflow(
        ToolsWorkflow.run,
        "What is the weather in Tokio?",
        id="tools-workflow",
        task_queue="my-task-queue",
        id_reuse_policy=WorkflowIDReusePolicy.TERMINATE_IF_RUNNING,
    )

    print(f"Result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
