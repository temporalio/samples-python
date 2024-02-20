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
            return result
        except Exception:
            activity.heartbeat("Invoking activity")
