"""
This file demonstrates how to define operation handlers by using a "shorthand" style in
which you implement the `start` method only. WorkflowRunOperationHandler implements
`cancel` for you automatically, but apart from that, the other operation methods
(`fetch_info`, `fetch_result`, and `cancel` for SyncOperationHandler) are all
automatically created with "raise NotImplementedError" implementations.

See hello_nexus/basic/handler/service_handler_with_operation_handler_classes.py for the
alternative "fully manual" style where you implement an OperationHandler class directly.
"""

from __future__ import annotations

import uuid

from nexusrpc.handler import StartOperationContext, service_handler, sync_operation
from temporalio import nexus
from temporalio.nexus import workflow_run_operation

from hello_nexus.basic.handler.db_client import MyDBClient
from hello_nexus.basic.handler.workflows import WorkflowStartedByNexusOperation
from hello_nexus.basic.service import MyInput, MyNexusService, MyOutput


@service_handler(service=MyNexusService)
class MyNexusServiceHandler:
    # You can create an __init__ method accepting what is needed by your operation
    # handlers to handle requests. You typically instantiate your service handler class
    # when starting your worker. See hello_nexus/basic/handler/worker.py.
    def __init__(self, connected_db_client: MyDBClient):
        # `connected_db_client` is intended as an example of something that might be
        # required by your operation handlers when handling requests, but is only
        # available at worker-start time.
        self.connected_db_client = connected_db_client

    # This is a nexus operation that is backed by a Temporal workflow. The start method
    # starts a workflow, and returns a nexus operation token. Meanwhile, the workflow
    # executes in the background; Temporal server takes care of delivering the eventual
    # workflow result (success or failure) to the calling workflow.
    #
    # The token will be used by the caller if it subsequently wants to cancel the Nexus
    # operation.
    @workflow_run_operation
    async def my_workflow_run_operation(
        self, ctx: StartOperationContext, input: MyInput
    ) -> nexus.WorkflowHandle[MyOutput]:
        # You could use self.connected_db_client here.
        return await nexus.start_workflow(
            WorkflowStartedByNexusOperation.run,
            input,
            id=str(uuid.uuid4()),
        )

    # This is a Nexus operation that responds synchronously to all requests. That means
    # that unlike the workflow run operation above, in this case the `start` method
    # returns the final operation result.
    #
    # Here it is implemented using SyncOperationHandler.from_callable.
    # See service_handler_with_operation_handler_classes.py for an alternative style
    # involving subclassing SyncOperationHandler and overriding the start method.
    #
    # Sync operations are free to make arbitrary network calls, or perform CPU-bound
    # computations. Total execution duration must not exceed 10s.
    @sync_operation
    async def my_sync_operation(
        self, ctx: StartOperationContext, input: MyInput
    ) -> MyOutput:
        # You could use self.connected_db_client here.
        return MyOutput(message=f"Hello {input.name} from sync operation!")
