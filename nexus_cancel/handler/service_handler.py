"""
This file demonstrates how to implement a Nexus service handler with a
workflow-backed operation that can be cancelled.

This sample reuses the service definition from hello_nexus but uses a custom
workflow implementation that demonstrates cancellation handling.
"""

from __future__ import annotations

import nexusrpc
from temporalio import nexus

from hello_nexus.service import MyInput, MyNexusService, MyOutput
from nexus_cancel.handler.workflows import HelloHandlerWorkflow


@nexusrpc.handler.service_handler(service=MyNexusService)
class MyNexusServiceHandler:
    """
    Handler for MyNexusService that demonstrates cancellation.

    This handler implements the workflow run operation using a workflow that
    handles cancellation gracefully.
    """

    @nexus.workflow_run_operation
    async def my_workflow_run_operation(
        self, ctx: nexus.WorkflowRunOperationContext, input: MyInput
    ) -> nexus.WorkflowHandle[MyOutput]:
        """
        Start a workflow that can be cancelled.

        The workflow will receive an asyncio.CancelledError when the caller
        requests cancellation.
        """
        # Use the request ID as the workflow ID for idempotency
        return await ctx.start_workflow(
            HelloHandlerWorkflow.run,
            input,
            id=f"hello-handler-{ctx.request_id}",
        )

    # Note: In a real implementation, you would also implement my_sync_operation
    # from the service. For this cancellation demo, we only implement the
    # workflow run operation which can be cancelled.
    @nexusrpc.handler.sync_operation
    async def my_sync_operation(
        self, ctx: nexusrpc.handler.StartOperationContext, input: MyInput
    ) -> MyOutput:
        """Sync operation that cannot be cancelled."""
        return MyOutput(message=f"Hello {input.name} from sync operation!")
