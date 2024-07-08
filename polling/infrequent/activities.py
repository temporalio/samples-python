from dataclasses import dataclass

from temporalio import activity

from polling.test_service import TestService


@dataclass
class ComposeGreetingInput:
    greeting: str
    name: str


class ComposeGreeting:
    def __init__(self):
        self.test_service = TestService()

    @activity.defn
    async def compose_greeting(self, input: ComposeGreetingInput) -> str:
        # If this raises an exception because it's not done yet, the activity will
        # continually be scheduled for retry
        return await self.test_service.get_service_result(input)
