import asyncio

from temporalio.client import Client
from temporalio.envconfig import ClientConfigProfile

from replay.worker import JustActivity, JustTimer, TimerThenActivity


async def main():
    # Connect client
    config_dict = ClientConfigProfile.load().to_dict()
    config_dict.setdefault("address", "localhost:7233")
    config = ClientConfigProfile.from_dict(config_dict)
    client = await Client.connect(**config.to_client_connect_config())

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
