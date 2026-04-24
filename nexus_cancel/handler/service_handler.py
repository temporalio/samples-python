"""
Nexus service handler for the cancellation sample.

The hello operation is backed by a workflow whose ID is derived from the
operation input (name + language), giving each fan-out branch a distinct,
meaningful business ID.
"""

from __future__ import annotations

import uuid

import nexusrpc
from temporalio import nexus

from nexus_cancel.handler.workflows import HelloHandlerWorkflow
from nexus_cancel.service import HelloInput, HelloOutput, NexusService


@nexusrpc.handler.service_handler(service=NexusService)
class NexusServiceHandler:
    @nexus.workflow_run_operation
    async def hello(
        self, ctx: nexus.WorkflowRunOperationContext, input: HelloInput
    ) -> nexus.WorkflowHandle[HelloOutput]:
        return await ctx.start_workflow(
            HelloHandlerWorkflow.run,
            input,
            id=f"hello-handler-{input.name}-{input.language.name}-{uuid.uuid4()}",
        )
