"""Temporal operation handler that starts a standalone Activity."""

from datetime import timedelta

import nexusrpc.handler
from temporalio import nexus

from nexus_standalone_activity.activity import create_greeting
from nexus_standalone_activity.service import (
    GreetingInput,
    GreetingOutput,
    GreetingService,
)


def get_activity_id(input: GreetingInput) -> str:
    return f"greeting-{input.name}"


@nexusrpc.handler.service_handler(service=GreetingService)
class GreetingServiceHandler:
    @nexus.temporal_operation
    async def greet(
        self,
        _ctx: nexus.TemporalStartOperationContext,
        client: nexus.TemporalNexusClient,
        input: GreetingInput,
    ) -> nexus.TemporalOperationResult[GreetingOutput]:
        # The standalone Activity becomes the asynchronous backing execution for
        # this Nexus operation. Omitting task_queue uses the Nexus Worker's queue.
        return await client.start_activity(
            create_greeting,
            input,
            id=get_activity_id(input),
            start_to_close_timeout=timedelta(seconds=10),
        )
