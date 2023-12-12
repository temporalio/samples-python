import asyncio

from temporalio.client import Client, WorkflowHandle

from workflow_update import HelloWorldWorkflow


class WorkflowRunner:
    def __init__(self, client: Client):
        self.client = client

    async def start_workflow(self) -> WorkflowHandle:
        return await self.client.start_workflow(
            HelloWorldWorkflow.execute_workflow,
            id="hello-world-update-workflow",
            task_queue="workflow-update-task-queue",
        )


async def run_workflow():
    client = await Client.connect("localhost:7233")
    runner = WorkflowRunner(client)

    # Start the workflow
    handle = await runner.start_workflow()

    # Perform the update
    update_result = await handle.execute_update(
        HelloWorldWorkflow.update_workflow_status
    )
    print(f"Update Result: {update_result}")

    # Get the workflow result
    result = await handle.result()
    print(f"Workflow Result: {result}")


if __name__ == "__main__":
    asyncio.run(run_workflow())
