"""
This file demonstrates how to define operation handlers by implementing an OperationHandler
class directly.

See hello_nexus/basic/handler/service_handler.py for the alternative "shorthand" style
where you implement the `start` method only.

Sync operations:
---------------
Implementations are free to make arbitrary network calls, or perform CPU-bound
computations such as this one. Total execution duration must not exceed 10s.


Workflow operations:
---------------------
The task queue defaults to the task queue being used by the Nexus worker.
"""

from __future__ import annotations

import uuid

from nexusrpc import OperationInfo
from nexusrpc.handler import (
    CancelOperationContext,
    FetchOperationInfoContext,
    FetchOperationResultContext,
    OperationHandler,
    StartOperationContext,
    StartOperationResultAsync,
    StartOperationResultSync,
    operation_handler,
    service_handler,
)
from temporalio import nexus

from hello_nexus.basic.handler.db_client import MyDBClient
from hello_nexus.basic.handler.service_handler import MyInput, MyNexusService, MyOutput
from hello_nexus.basic.handler.workflows import WorkflowStartedByNexusOperation


@service_handler(service=MyNexusService)
class MyNexusServiceHandlerUsingOperationHandlerClasses:
    # You can create an __init__ method accepting what is needed by your operation
    # handlers to handle requests. You typically instantiate your service handler class
    # when starting your worker. See hello_nexus/basic/handler/worker.py.
    def __init__(self, connected_db_client: MyDBClient):
        # `connected_db_client` is intended as an example of something that might be
        # required by your operation handlers when handling requests, but is only
        # available at worker-start time.
        self.connected_db_client = connected_db_client

    @operation_handler
    def my_sync_operation(self) -> OperationHandler[MyInput, MyOutput]:
        # Pass any required arguments to the OperationHandler __init__ method here.
        return MySyncOperation()

    @operation_handler
    def my_workflow_run_operation(
        self,
    ) -> OperationHandler[MyInput, MyOutput]:
        # Pass any required arguments to the OperationHandler __init__ method here.
        return MyWorkflowRunOperation()


# This is a Nexus operation that is backed by a Temporal workflow. That means that it
# responds asynchronously to all requests: it starts a workflow and responds with a token
# that the handler can associate with the worklow is started.
class MyWorkflowRunOperation(OperationHandler[MyInput, MyOutput]):
    # You can add an __init__ method taking any required arguments, since you are in
    # control of instantiating the OperationHandler inside the operation handler method
    # above decorated with @operation_handler.

    # The start method starts a workflow, and returns a StartOperationResultAsync that it
    # creates from the workflow handle. This return value contains the Nexus operation
    # token that the handler can use to obtain a handle and interact with the workflow on
    # future requests (for example if a cancel request is subsequently sent by the
    # caller). The Temporal server takes care of delivering the workflow result to the
    # calling workflow. The task queue defaults to the task queue being used by the Nexus
    # worker.
    async def start(
        self, ctx: StartOperationContext, input: MyInput
    ) -> StartOperationResultAsync:
        handle = await nexus.start_workflow(
            WorkflowStartedByNexusOperation.run,
            input,
            id=str(uuid.uuid4()),
        )
        return StartOperationResultAsync(handle.to_token())

    async def fetch_info(
        self, ctx: FetchOperationInfoContext, input: MyInput
    ) -> OperationInfo:
        raise NotImplementedError

    async def cancel(self, ctx: CancelOperationContext, input: MyInput) -> None:
        raise NotImplementedError

    async def fetch_result(
        self, ctx: FetchOperationResultContext, input: MyInput
    ) -> MyOutput:
        raise NotImplementedError


# This is a Nexus operation that responds synchronously to all requests. That means that
# unlike the workflow run operation above, in this case the `start` method returns the
# final operation result.
#
# Here it is implemented by subclassing SyncOperationHandler and overriding the start
# method. See service_handler.py for an alternative style using
# SyncOperationHandler.from_callable.
#
# Sync operations are free to make arbitrary network calls, or perform CPU-bound
# computations. Total execution duration must not exceed 10s.
class MySyncOperation(OperationHandler[MyInput, MyOutput]):
    # You can add an __init__ method taking any required arguments, since you are in
    # control of instantiating the OperationHandler inside the operation handler method
    # above decorated with @operation_handler.

    # Unlike the workflow run operation below, the `start` method for a sync operation
    # returns the final operation result. Sync operations are free to make arbitrary
    # network calls, or perform CPU-bound computations. Total execution duration must not
    # exceed 10s. async def start(
    async def start(
        self, ctx: StartOperationContext, input: MyInput
    ) -> StartOperationResultSync[MyOutput]:
        output = MyOutput(message=f"Hello {input.name} from sync operation!")
        return StartOperationResultSync(output)

    async def fetch_info(
        self, ctx: FetchOperationInfoContext, input: MyInput
    ) -> OperationInfo:
        raise NotImplementedError

    async def cancel(self, ctx: CancelOperationContext, input: MyInput) -> None:
        raise NotImplementedError

    async def fetch_result(
        self, ctx: FetchOperationResultContext, input: MyInput
    ) -> MyOutput:
        raise NotImplementedError
