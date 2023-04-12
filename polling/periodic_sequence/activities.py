from obj import ComposeGreetingInput
from temporalio import activity


@activity.defn
async def compose_greeting(input: ComposeGreetingInput) -> str:
    print(f"Invoking activity, attempt number {activity.info().attempt}")
    # Fail the first 4 attempts, succeed the 5th
    if activity.info().attempt < 5:
        raise RuntimeError("Service is down")
    return f"{input.greeting}, {input.name}!"
