import asyncio
from datetime import timedelta

from temporalio import activity, workflow
from temporalio.client import Client
from temporalio.envconfig import ClientConfig
from temporalio.worker import Worker

from util import get_temporal_config_path


class MyDatabaseClient:
    async def run_database_update(self) -> None:
        print("Database update executed")


class MyActivities:
    def __init__(self, db_client: MyDatabaseClient) -> None:
        self.db_client = db_client

    @activity.defn
    async def do_database_thing(self) -> None:
        await self.db_client.run_database_update()


@workflow.defn
class MyWorkflow:
    @workflow.run
    async def run(self) -> None:
        await workflow.execute_activity_method(
            MyActivities.do_database_thing,
            start_to_close_timeout=timedelta(seconds=10),
        )


async def main():
    # Start client
    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")
    client = await Client.connect(**config)

    # Create our database client that can then be used in the activity
    db_client = MyDatabaseClient()
    # Instantiate our class containing state that can be referenced from
    # activity methods
    my_activities = MyActivities(db_client)

    # Run a worker for the workflow
    async with Worker(
        client,
        task_queue="hello-activity-method-task-queue",
        workflows=[MyWorkflow],
        activities=[my_activities.do_database_thing],
    ):

        # While the worker is running, use the client to run the workflow and
        # print out its result. Note, in many production setups, the client
        # would be in a completely separate process from the worker.
        await client.execute_workflow(
            MyWorkflow.run,
            id="hello-activity-method-workflow-id",
            task_queue="hello-activity-method-task-queue",
        )


if __name__ == "__main__":
    asyncio.run(main())
