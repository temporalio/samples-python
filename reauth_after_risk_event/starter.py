import asyncio
from datetime import timedelta
from temporalio.client import Client

async def main():
    client = await Client.connect("localhost:7233")

    result = await client.start_workflow(
        "ReauthenticationAfterRiskEventWorkflow",
        "user-123",  # user_id
        id="reauth-workflow-user-123",
        task_queue="reauth-task-queue",
        run_timeout=timedelta(minutes=1),  # Correct timeout usage
    )

    print(f"Started workflow. Run ID: {result.id}")

if __name__ == "__main__":
    asyncio.run(main())
