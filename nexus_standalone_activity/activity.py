"""Activity used as the backing execution for the Nexus operation."""

from temporalio import activity

from nexus_standalone_activity.service import GreetingInput, GreetingOutput


@activity.defn
async def create_greeting(input: GreetingInput) -> GreetingOutput:
    return GreetingOutput(message=f"Hello, {input.name}!")
