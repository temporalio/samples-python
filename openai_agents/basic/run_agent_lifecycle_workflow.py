import asyncio

from temporalio.client import Client

from openai_agents.basic.workflows.agent_lifecycle_workflow import (
    AgentLifecycleWorkflow,
)


async def main() -> None:
        # Get repo root - 2 levels deep from root
        repo_root = Path(__file__).resolve().parent.parent.parent
        config_file = repo_root / "temporal.toml"
    config = ClientConfig.load_client_connect_config(config_file=str(config_file))
    config["target_host"] = "localhost:7233"
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
