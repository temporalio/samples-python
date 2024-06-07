import asyncio
import time
from dataclasses import dataclass

from temporalio import activity

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
            activity.logger.info(f"Exiting activity ${result}")
            return result
        except Exception as e:
            # swallow exception since service is down
            activity.logger.error(e)

        try:
            activity.heartbeat("Invoking activity")
        except asyncio.CancelledError as exception:
            # activity was either cancelled or workflow was completed or worker shut down
            # if you need to clean up you can catch this. Here we are just reraising exception
            raise

        await asyncio.sleep(1)
