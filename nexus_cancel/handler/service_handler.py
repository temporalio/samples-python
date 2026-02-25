"""
Nexus service handler for the cancellation sample.

The hello operation is backed by a workflow, using the Nexus request ID as the
workflow ID for idempotency across retries.
"""

from __future__ import annotations

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
            id=ctx.request_id,
        )
