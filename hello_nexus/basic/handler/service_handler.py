"""
This file demonstrates how to define operation handlers by using the "shorthand"
decorators sync_operation_handler and workflow_run_operation_handler. In this style you
implement the `start` method only. workflow_run_operation_handler implements `cancel` for
you automatically, but apart from that, the other operation methods (`fetch_info`,
`fetch_result`, and `cancel` for sync_operation_handler) are all automatically created
with "raise NotImplementedError" implementations.

See hello_nexus/basic/handler/service_handler_with_operation_handler_classes.py for the
alternative "fully manual" style where you implement an OperationHandler class directly.
"""

from __future__ import annotations

import uuid

import nexusrpc.handler
import temporalio.common
import temporalio.nexus
import temporalio.nexus.handler
from nexusrpc.handler import (
    StartOperationContext,
    service_handler,
    sync_operation_handler,
)
from temporalio.nexus.handler import (
    NexusStartWorkflowRequest,
    TemporalNexusOperationContext,
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
    # starts a workflow, and returns a nexus operation token that the handler can use to
    # obtain a workflow handle (for example if a cancel request is subsequently sent by
    # the caller). The Temporal server takes care of delivering the workflow result to the
    # calling workflow. The task queue defaults to the task queue being used by the Nexus
    # worker.
    @temporalio.nexus.handler.workflow_run_operation_handler
    async def my_workflow_run_operation(
        self, ctx: StartOperationContext, input: MyInput
    ) -> NexusStartWorkflowRequest[MyOutput]:
        # You could use self.connected_db_client here.
        tctx = TemporalNexusOperationContext.current()
        return NexusStartWorkflowRequest(
            tctx.client.start_workflow(
                WorkflowStartedByNexusOperation.run,
                input,
                id=str(uuid.uuid4()),
                task_queue=tctx.task_queue,
            )
        )

    # This is a sync operation. That means that unlike the workflow run operation above,
    # in this case the `start` method returns the final operation result. Sync operations
    # are free to make arbitrary network calls, or perform CPU-bound computations. Total
    # execution duration must not exceed 10s.
    @sync_operation_handler
    async def my_sync_operation(
        self, ctx: nexusrpc.handler.StartOperationContext, input: MyInput
    ) -> MyOutput:
        # You could use self.connected_db_client here.
        return MyOutput(message=f"Hello {input.name} from sync operation!")
