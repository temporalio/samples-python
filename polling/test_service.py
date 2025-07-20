from dataclasses import dataclass
from typing import Counter

from temporalio import activity
from temporalio.exceptions import ApplicationError, ApplicationErrorCategory

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
    raise ApplicationError(
        message="service is down",
        # Set the error as BENIGN to indicate it is an expected error.
        # BENIGN errors have activity failure logs downgraded to DEBUG level
        # and do not emit activity failure metrics.
        category=ApplicationErrorCategory.BENIGN,
    )
