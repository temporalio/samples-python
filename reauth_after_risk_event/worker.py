import asyncio
from temporalio.worker import Worker
from temporalio.client import Client
from workflow import ReauthenticationAfterRiskEventWorkflow

async def main():
    client = await Client.connect("localhost:7233")
    worker = Worker(
        client,
        task_queue="reauth-task-queue",
        workflows=[ReauthenticationAfterRiskEventWorkflow],
    )
    print("Worker started.")
    await worker.run()

if __name__ == "__main__":
    asyncio.run(main())
