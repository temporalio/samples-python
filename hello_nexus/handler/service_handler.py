"""
This file demonstrates how to implement a Nexus service.
"""

from __future__ import annotations

import uuid

import nexusrpc
from temporalio import nexus

from hello_nexus.handler.workflows import WorkflowStartedByNexusOperation
from hello_nexus.service import MyInput, MyNexusService, MyOutput


@nexusrpc.handler.service_handler(service=MyNexusService)
class MyNexusServiceHandler:
    # You can create an __init__ method accepting what is needed by your operation
    # handlers to handle requests. You typically instantiate your service handler class
    # when starting your worker. See hello_nexus/basic/handler/worker.py.

    # This is a nexus operation that is backed by a Temporal workflow. The start method
    # starts a workflow, and returns a nexus operation token. Meanwhile, the workflow
    # executes in the background; Temporal server takes care of delivering the eventual
    # workflow result (success or failure) to the calling workflow.
    #
    # The token will be used by the caller if it subsequently wants to cancel the Nexus
    # operation.
    @nexus.workflow_run_operation
    async def my_workflow_run_operation(
        self, ctx: nexus.WorkflowRunOperationContext, input: MyInput
    ) -> nexus.WorkflowHandle[MyOutput]:
        return await ctx.start_workflow(
            WorkflowStartedByNexusOperation.run,
            input,
            id=str(uuid.uuid4()),
        )

    # This is a Nexus operation that responds synchronously to all requests. That means
    # that unlike the workflow run operation above, in this case the `start` method
    # returns the final operation result.
    #
    # Sync operations are free to make arbitrary network calls, or perform CPU-bound
    # computations. Total execution duration must not exceed 10s.
    @nexusrpc.handler.sync_operation
    async def my_sync_operation(
        self, ctx: nexusrpc.handler.StartOperationContext, input: MyInput
    ) -> MyOutput:
        return MyOutput(message=f"Hello {input.name} from sync operation!")
