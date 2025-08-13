import asyncio

from temporalio.client import Client
from temporalio.envconfig import ClientConfigProfile

from openai_agents.basic.workflows.agent_lifecycle_workflow import (
    AgentLifecycleWorkflow,
)


async def main() -> None:
    config_dict = ClientConfigProfile.load().to_dict()
    config_dict.setdefault("address", "localhost:7233")
    config = ClientConfigProfile.from_dict(config_dict)
    client = await Client.connect(**config.to_client_connect_config())

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
