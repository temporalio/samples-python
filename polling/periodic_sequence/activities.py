from typing import Any, NoReturn

from temporalio import activity


@activity.defn
async def compose_greeting(input: Any) -> NoReturn:
    raise RuntimeError("Service is down")
