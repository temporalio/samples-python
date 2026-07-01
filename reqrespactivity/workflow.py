# workflow.py
import asyncio
from datetime import timedelta
from dataclasses import dataclass
from temporalio import workflow, activity

# Define data models similar to the Go structs.
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

# Activity to convert text to uppercase.
@activity.defn
async def uppercase_activity(text: str) -> str:
    return text.upper()

# Workflow that listens for "request" signals.
@workflow.defn
class UppercaseWorkflow:
    def __init__(self):
        self.requests = []  # Buffer for incoming requests

    @workflow.signal
    def request(self, req: Request):
        self.requests.append(req)

    @workflow.run
    async def run(self):
        # Continuously process incoming requests.
        while True:
            if self.requests:
                req = self.requests.pop(0)
                try:
                    # Execute the uppercase activity.
                    result = await workflow.execute_activity(
                        uppercase_activity,
                        req.input,
                        start_to_close_timeout=timedelta(seconds=5),
                    )
                    resp = Response(id=req.id, output=result)
                except Exception as e:
                    resp = Response(id=req.id, output="", error=str(e))
                # Call back the requester via the designated response activity.
                await workflow.execute_activity(
                    req.response_activity,
                    resp,
                    task_queue=req.response_task_queue,
                    start_to_close_timeout=timedelta(seconds=10),
                )
            else:
                await workflow.sleep(1)
