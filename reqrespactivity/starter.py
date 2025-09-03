# starter.py
import asyncio
from temporalio.client import Client
from workflow import UppercaseWorkflow

async def main():
    client = await Client.connect("localhost:7233")
    workflow_id = "reqrespactivity_workflow"
    handle = await client.start_workflow(
        UppercaseWorkflow.run,
        id=workflow_id,
        task_queue="reqrespactivity",
    )
    print(f"Started workflow with ID: {handle.id}")

if __name__ == "__main__":
    asyncio.run(main())
