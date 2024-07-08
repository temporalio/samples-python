from dataclasses import dataclass

from temporalio import activity

from polling.test_service import TestService


@dataclass
class ComposeGreetingInput:
    greeting: str
    name: str


@activity.defn
async def compose_greeting(input: ComposeGreetingInput) -> str:
    attempt = activity.info().attempt - 1
    test_service = TestService(attempt=attempt)
    # If this raises an exception because it's not done yet, the activity will
    # continually be scheduled for retry
    return await test_service.get_service_result(input)
