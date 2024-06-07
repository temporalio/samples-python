import asyncio
import time
from dataclasses import dataclass

from temporalio import activity
from temporalio.exceptions import CancelledError

from polling.test_service import TestService


@dataclass
class ComposeGreetingInput:
    greeting: str
    name: str


@activity.defn
async def compose_greeting(input: ComposeGreetingInput) -> str:
    test_service = TestService()
    while True:
        try:
            result = test_service.get_service_result(input)
            print(f"exiting activity ${result}")
            return result
        except Exception as e:
            # swallow exception since service is down
            print(e)

        try:
            activity.heartbeat("Invoking activity")
        except CancelledError as exception:
            # activity was either cancelled or workflow was completed or worker shut down
            raise exception

        await asyncio.sleep(1)
