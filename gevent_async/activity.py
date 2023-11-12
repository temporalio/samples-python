from dataclasses import dataclass

import gevent
from temporalio import activity


@dataclass
class ComposeGreetingInput:
    greeting: str
    name: str


@activity.defn
async def compose_greeting_async(input: ComposeGreetingInput) -> str:
    activity.logger.info(f"Running async activity with parameter {input}")
    return f"{input.greeting}, {input.name}!"


@activity.defn
def compose_greeting_sync(input: ComposeGreetingInput) -> str:
    activity.logger.info(
        f"Running sync activity with parameter {input}, "
        f"in greenlet: {gevent.getcurrent()}"
    )
    return f"{input.greeting}, {input.name}!"
