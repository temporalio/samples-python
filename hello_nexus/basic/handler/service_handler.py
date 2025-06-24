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

from nexusrpc.handler import (
    OperationHandler,
    StartOperationContext,
    SyncOperationHandler,
    operation_handler,
    service_handler,
)
from temporalio.nexus.handler import (
    WorkflowOperationToken,
    WorkflowRunOperationHandler,
    start_workflow,
)

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
    # starts a workflow, and returns a nexus operation token synchronously. Meanwhile,
    # the workflow executes in the background, and the Temporal server takes care of
    # delivering the eventual workflow result (success or failure) to the calling
    # workflow.
    #
    # The token will be used by the caller if it subsequently wants to cancel the Nexus
    # operation.
    @operation_handler
    def my_workflow_run_operation(
        self,
    ) -> OperationHandler[MyInput, MyOutput]:
        async def start(
            ctx: StartOperationContext, input: MyInput
        ) -> WorkflowOperationToken[MyOutput]:
            # You could use self.connected_db_client here.
            return await start_workflow(
                WorkflowStartedByNexusOperation.run,
                input,
                id=str(uuid.uuid4()),
            )

        return WorkflowRunOperationHandler(start)

    # This is a sync operation. That means that unlike the workflow run operation above,
    # in this case the `start` method returns the final operation result. Sync operations
    # are free to make arbitrary network calls, or perform CPU-bound computations. Total
    # execution duration must not exceed 10s.
    @operation_handler
    def my_sync_operation(
        self,
    ) -> OperationHandler[MyInput, MyOutput]:
        async def start(ctx: StartOperationContext, input: MyInput) -> MyOutput:
            # You could use self.connected_db_client here.
            return MyOutput(message=f"Hello {input.name} from sync operation!")

        return SyncOperationHandler(start)
