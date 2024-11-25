from collections import Counter
from dataclasses import dataclass

from temporalio import activity

attempts = Counter()
ERROR_ATTEMPTS = 5


@dataclass
class ComposeGreetingInput:
    greeting: str
    name: str


async def get_service_result(input):
    attempts[activity.info().workflow_id] += 1
    attempt = attempts[activity.info().workflow_id]

    print(f"Attempt {attempt} of {ERROR_ATTEMPTS} to invoke service")
    if attempt == ERROR_ATTEMPTS:
        return f"{input.greeting}, {input.name}!"
    raise Exception("service is down")
