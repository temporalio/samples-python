from dataclasses import dataclass
from typing import Counter

from temporalio import activity

attempts = Counter[str]()
ERROR_ATTEMPTS = 5


@dataclass
class ComposeGreetingInput:
    greeting: str
    name: str


async def get_service_result(input):
    workflow_id = activity.info().workflow_id
    attempts[workflow_id] += 1

    print(f"Attempt {attempts[workflow_id]} of {ERROR_ATTEMPTS} to invoke service")
    if attempts[workflow_id] == ERROR_ATTEMPTS:
        return f"{input.greeting}, {input.name}!"
    raise Exception("service is down")
