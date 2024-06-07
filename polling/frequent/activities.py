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
            try:
                result = await test_service.get_service_result(input)
                activity.logger.info(f"Exiting activity ${result}")
                return result
            except Exception as e:
                # swallow exception since service is down
                activity.logger.debug("Failed, trying again shortly", exc_info=True)

            activity.heartbeat("Invoking activity")
            await asyncio.sleep(1)
        except asyncio.CancelledError:
            # activity was either cancelled or workflow was completed or worker shut down
            # if you need to clean up you can catch this.
            # Here we are just reraising the exception
            raise

