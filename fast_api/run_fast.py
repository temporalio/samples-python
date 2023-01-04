import asyncio

from fastapi import FastAPI
from temporalio.client import Client

from fast_api.run_worker import SayHello

app = FastAPI()


@app.get("/")
async def main():
    # Create client connected to server at the given address
    client = await Client.connect("localhost:7233")

    # Execute a workflow
    result = await client.execute_workflow(
        SayHello.run, "World", id="my-workflow-id", task_queue="my-task-queue"
    )
    print(f"{result}")
    return result


if __name__ == "__main__":
    asyncio.run(main())
