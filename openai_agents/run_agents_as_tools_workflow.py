import asyncio

from temporalio.client import Client
from temporalio.common import WorkflowIDReusePolicy

# from openai_agents.adapters.open_ai_converter import open_ai_data_converter
from openai_agents.workflows.agents_as_tools_workflow import AgentsAsToolsWorkflow


async def main():
    # Create client connected to server at the given address
    client = await Client.connect("localhost:7233")

    # Execute a workflow
    result = await client.execute_workflow(
        AgentsAsToolsWorkflow.run,
        "Translate to English: '¿Cómo estás?'",
        id="my-workflow-id",
        task_queue="my-task-queue",
        id_reuse_policy=WorkflowIDReusePolicy.TERMINATE_IF_RUNNING,
    )

    print(f"Result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
