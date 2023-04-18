import asyncio
from dataclasses import dataclass

from temporalio import activity


@dataclass
class ComposeGreetingInput:
    greeting: str
    name: str


@activity.defn
async def compose_greeting(input: ComposeGreetingInput) -> str:
    print(f"Invoking activity, attempt number {activity.info().attempt}")
    # Fail the first 4 attempts, succeed the 5th
    if activity.info().attempt < 5:
        await asyncio.sleep(1)
        raise RuntimeError("Service is down")
    return f"{input.greeting}, {input.name}!"
