# worker.py
import asyncio
from temporalio.client import Client
from temporalio.worker import Worker
from workflow import UppercaseWorkflow, uppercase_activity

async def main():
    client = await Client.connect("localhost:7233")
    worker = Worker(
        client,
        task_queue="reqrespactivity",
        workflows=[UppercaseWorkflow],
        activities=[uppercase_activity],
    )
    print("Worker started on task queue 'reqrespactivity'")
    await worker.run()

if __name__ == "__main__":
    asyncio.run(main())
