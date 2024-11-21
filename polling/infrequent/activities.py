from temporalio import activity

from polling.test_service import ComposeGreetingInput, TestService


@activity.defn
async def compose_greeting(input: ComposeGreetingInput) -> str:
    test_service = TestService()
    # If this raises an exception because it's not done yet, the activity will
    # continually be scheduled for retry
    return await test_service.get_service_result(input)
