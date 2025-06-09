# requester_run.py
import asyncio
from temporalio.client import Client
from requester import Requester

async def main():
    client = await Client.connect("localhost:7233")
    workflow_id = "reqrespactivity_workflow"
    requester = Requester(client, workflow_id)
    await requester.start_worker()
    try:
        i = 0
        while True:
            text = f"foo{i}"  # Create request similar to the Go sample: foo0, foo1, etc.
            result = await requester.request_uppercase(text)
            print(f"Requested uppercase for '{text}', got: '{result}'")
            await asyncio.sleep(1)
            i += 1
    finally:
        await requester.close()

if __name__ == "__main__":
    asyncio.run(main())
