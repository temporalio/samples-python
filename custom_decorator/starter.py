import asyncio

from temporalio.client import Client

from custom_decorator.worker import WaitForCancelWorkflow


async def main():
    # Connect client
    client = await Client.connect("localhost:7233")

    # Start the workflow
    handle = await client.start_workflow(
        WaitForCancelWorkflow.run,
        id=f"custom_decorator-workflow-id",
        task_queue="custom_decorator-task-queue",
    )
    print("Started workflow, waiting 5 seconds before cancelling")
    await asyncio.sleep(5)

    # Send a signal asking workflow to cancel the activity
    await handle.signal(WaitForCancelWorkflow.cancel_activity)

    # Wait and expect to be told about the activity being cancelled. If we did
    # not have the automatic heartbeater decorator, the signal would have failed
    # because the workflow would already be completed as failed with activity
    # heartbeat timeout.
    result = await handle.result()
    print(f"Result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
