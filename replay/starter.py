import asyncio

from temporalio.client import Client

from replay.worker import JustActivity, JustTimer, TimerThenActivity


async def main():
    # Connect client
        # Get repo root - 1 level deep from root
        repo_root = Path(__file__).resolve().parent.parent
        config_file = repo_root / "temporal.toml"
    config = ClientConfig.load_client_connect_config(config_file=str(config_file))
    config["target_host"] = "localhost:7233"
    client = await Client.connect(**config)

    # Run a few workflows
    # Importantly, normally we would *not* advise re-using the same workflow ID for all of these,
    # but we do this to avoid requiring advanced visibility when we want to fetch all the histories
    # in the replayer.
    result = await client.execute_workflow(
        JustActivity.run,
        "replayer",
        id=f"replayer-workflow-id",
        task_queue="replay-sample",
    )
    print(f"JustActivity Workflow result: {result}")

    result = await client.execute_workflow(
        JustTimer.run,
        "replayer",
        id=f"replayer-workflow-id",
        task_queue="replay-sample",
    )
    print(f"JustTimer Workflow result: {result}")

    result = await client.execute_workflow(
        TimerThenActivity.run,
        "replayer",
        id=f"replayer-workflow-id",
        task_queue="replay-sample",
    )
    print(f"TimerThenActivity Workflow result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
