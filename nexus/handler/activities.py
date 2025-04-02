import asyncio

from temporalio import activity

from nexus.service.interface import (
    HelloInput,
    HelloOutput,
)


@activity.defn
async def hello_activity(input: HelloInput) -> HelloOutput:
    await asyncio.sleep(1)
    return HelloOutput(message=f"hello {input.name}")
