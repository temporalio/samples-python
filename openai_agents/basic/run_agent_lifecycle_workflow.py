import asyncio

from temporalio.client import Client

from openai_agents.basic.workflows.agent_lifecycle_workflow import (
    AgentLifecycleWorkflow,
)


async def main() -> None:
    client = await Client.connect("localhost:7233")

    user_input = input("Enter a max number: ")
    max_number = int(user_input)

    result = await client.execute_workflow(
        AgentLifecycleWorkflow.run,
        max_number,
        id="agent-lifecycle-workflow",
        task_queue="openai-agents-basic-task-queue",
    )

    print(f"Final result: {result}")
    print("Done!")


if __name__ == "__main__":
    asyncio.run(main())
