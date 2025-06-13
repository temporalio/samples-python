import asyncio

from temporalio.client import Client
from temporalio.common import WorkflowIDReusePolicy

from openai_agents.workflows.hello_world_workflow import HelloWorldAgent

from temporalio.contrib.openai_agents.temporal_openai_agents import (
    set_open_ai_agent_temporal_overrides,
)


async def main():
    # Create client connected to server at the given address
    client = await Client.connect("localhost:7233")

    with set_open_ai_agent_temporal_overrides():
        # Execute a workflow
        result = await client.execute_workflow(HelloWorldAgent.run, "Tell me about recursion in programming.",
                                            id="my-workflow-id", task_queue="my-task-queue",
                                            id_reuse_policy=WorkflowIDReusePolicy.TERMINATE_IF_RUNNING)
        print(f"Result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
