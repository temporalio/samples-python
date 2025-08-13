import asyncio

from temporalio import workflow
from temporalio.client import Client
from temporalio.envconfig import ClientConfigProfile
from temporalio.worker import Worker


@workflow.defn
class GreetingWorkflow:
    def __init__(self):
        self.is_complete = False

    @workflow.run
    async def run(self) -> str:
        await workflow.wait_condition(lambda: self.is_complete)
        return "Hello, World!"

    @workflow.update
    async def update_workflow_status(self) -> str:
        self.is_complete = True
        return "Workflow status updated"


async def main():
    config = ClientConfigProfile.load()
    config["address"] = "localhost:7233"
    client = await Client.connect(**config.to_client_connect_config())

    # Run a worker for the workflow
    async with Worker(
        client,
        task_queue="update-workflow-task-queue",
        workflows=[GreetingWorkflow],
    ):
        # While the worker is running, use the client to start the workflow.
        # Note, in many production setups, the client would be in a completely
        # separate process from the worker.
        handle = await client.start_workflow(
            GreetingWorkflow.run,
            id="hello-update-workflow-id",
            task_queue="update-workflow-task-queue",
        )

        # Perform the update for GreetingWorkflow
        update_result = await handle.execute_update(
            GreetingWorkflow.update_workflow_status
        )
        print(f"Update Result: {update_result}")

        # Get the result for GreetingWorkflow
        result = await handle.result()
        print(f"Workflow Result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
