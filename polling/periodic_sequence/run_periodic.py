import asyncio

from temporalio.client import Client

from polling.periodic_sequence.workflows import GreetingWorkflow


async def main():
        # Get repo root - 2 levels deep from root
        repo_root = Path(__file__).resolve().parent.parent.parent
        config_file = repo_root / "temporal.toml"
    config = ClientConfig.load_client_connect_config(config_file=str(config_file))
    config["target_host"] = "localhost:7233"
    client = await Client.connect(**config)
    result = await client.execute_workflow(
        GreetingWorkflow.run,
        "World",
        id="periodic-child-workflow-retry",
        task_queue="periodic-retry-task-queue",
    )
    print(f"Result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
