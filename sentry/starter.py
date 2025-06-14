import asyncio

from temporalio.client import Client

from sentry.workflow import GreetingWorkflow


async def main():
    # Connect client
    client = await Client.connect("localhost:7233")

    # Run workflow
    try:
        result = await client.execute_workflow(
            GreetingWorkflow.run,
            "World",
            id="sentry-workflow-id",
            task_queue="sentry-task-queue",
        )
        print(f"Workflow result: {result}")
    except Exception:
        print("Workflow failed - check Sentry for details")


if __name__ == "__main__":
    asyncio.run(main())
