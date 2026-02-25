# requester.py
import asyncio
import uuid
from dataclasses import dataclass
from temporalio import activity
from temporalio.client import Client
from temporalio.worker import Worker

# Global variable to hold the current Requester instance.
global_requester_instance = None

@dataclass
class Request:
    id: str
    input: str
    response_activity: str
    response_task_queue: str

@dataclass
class Response:
    id: str
    output: str
    error: str = ""

# Define the response activity as a top-level function with the decorator.
@activity.defn
async def response_activity(response: Response):
    global global_requester_instance
    if global_requester_instance:
        fut = global_requester_instance.pending.pop(response.id, None)
        if fut:
            fut.set_result(response)
    else:
        raise Exception("No requester instance available")

class Requester:
    def __init__(self, client: Client, target_workflow_id: str):
        self.client = client
        self.target_workflow_id = target_workflow_id
        self.task_queue = "requester-" + str(uuid.uuid4())
        self.pending = {}  # Maps request IDs to asyncio.Future objects

    async def start_worker(self):
        global global_requester_instance
        global_requester_instance = self  # Set the global reference
        self.worker = Worker(
            self.client,
            task_queue=self.task_queue,
            activities=[response_activity],
        )
        # Run the worker in the background.
        asyncio.create_task(self.worker.run())

    async def close(self):
        await self.worker.shutdown()

    async def request_uppercase(self, text: str) -> str:
        req_id = str(uuid.uuid4())
        req = Request(
            id=req_id,
            input=text,
            response_activity="response_activity",  # Must match the name of the decorated function
            response_task_queue=self.task_queue,
        )
        loop = asyncio.get_running_loop()
        fut = loop.create_future()
        self.pending[req_id] = fut

        # Get a handle to the workflow and send the signal.
        handle = self.client.get_workflow_handle(self.target_workflow_id)
        await handle.signal("request", req)

        # Wait for the callback to return the response.
        response: Response = await fut
        if response.error:
            raise Exception(response.error)
        return response.output
