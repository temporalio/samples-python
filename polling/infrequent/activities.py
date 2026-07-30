from temporalio import activity

from polling.test_service import ComposeGreetingInput, get_service_result


@activity.defn
async def compose_greeting(input: ComposeGreetingInput) -> str:
    # If this raises an exception because it's not done yet, the activity will
    # continually be scheduled for retry
    return await get_service_result(input)
