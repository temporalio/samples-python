import asyncio

from temporalio import workflow
from temporalio.client import Client
from temporalio.common import WorkflowIDReusePolicy

from openai_agents.workflows.hello_world_workflow import HelloWorldAgent

with workflow.unsafe.imports_passed_through():
    from temporalio.contrib.openai_agents.open_ai_data_converter import (
        open_ai_data_converter,
    )

async def main():
    # Create client connected to server at the given address
    client = await Client.connect(
        "localhost:7233",
        data_converter=open_ai_data_converter,
    )

    # Execute a workflow
    result = await client.execute_workflow(
        HelloWorldAgent.run,
        "Tell me about recursion in programming.",
        id="my-workflow-id",
        task_queue="my-task-queue",
        id_reuse_policy=WorkflowIDReusePolicy.TERMINATE_IF_RUNNING,
    )
    print(f"Result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
