import asyncio

from temporalio.client import Client
from temporalio.envconfig import ClientConfig

from openai_agents.basic.workflows.agent_lifecycle_workflow import (
    AgentLifecycleWorkflow,
)


async def main() -> None:
    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")
    client = await Client.connect(**config)

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
