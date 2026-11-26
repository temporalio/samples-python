"""Temporal operation handler that starts a standalone Activity."""

from datetime import timedelta

import nexusrpc.handler
from temporalio import activity, nexus

from nexus_completion_callbacks.service import (
    GreetingInput,
    GreetingOutput,
    GreetingService,
)


@activity.defn
async def create_greeting(input: GreetingInput) -> GreetingOutput:
    return GreetingOutput(message=f"Hello, {input.name}!")


@nexusrpc.handler.service_handler(service=GreetingService)
class GreetingServiceHandler:
    @nexus.temporal_operation
    async def greet(
        self,
        _ctx: nexus.TemporalStartOperationContext,
        client: nexus.TemporalNexusClient,
        input: GreetingInput,
    ) -> nexus.TemporalOperationResult[GreetingOutput]:
        return await client.start_activity(
            create_greeting,
            input,
            id=f"greeting-{input.name}",
            start_to_close_timeout=timedelta(seconds=10),
        )
