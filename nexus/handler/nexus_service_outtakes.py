"""
Notes:

Sync operations:
---------------
Implementations are free to make arbitrary network calls, or perform CPU-bound
computations such as this one. Total execution duration must not exceed 10s. To perform
Temporal client calls such as signaling/querying/listing workflows, use self.client.


Async operations:
----------------
The decorators `@temporalio.nexus.workflow_operation` and `@temporalio.nexus.activity_operation` are
conveniences: the user writes a method that starts the operation; cancel and fetch_info are
implemented for them. The task queue used by the defaults to the task queue beingused by the Nexus
worker.
"""

import nexusrpc.handler
import temporalio.nexus
from temporalio.nexus.handler import AsyncWorkflowOperationResult

from nexus.handler.dbclient import MyDBClient
from nexus.handler.workflows import HelloWorkflow
from nexus.service import interface
from nexus.service.interface import (
    EchoInput,
    EchoOutput,
    HelloInput,
    HelloOutput,
)


@nexusrpc.handler.service(interface.MyNexusService)
class MyNexusService:
    def __init__(self, db_client: MyDBClient):
        self.db_client = db_client

    # ----------------------------------------------------------------------------------
    #
    # Synchronous Nexus operation defined via convenience decorator.
    #
    # - The operation is sync from the caller's POV but the handler implementation is always an `async def`

    @nexusrpc.handler.sync_operation
    async def echo(
        self,
        input: EchoInput,
        options: nexusrpc.handler.OperationOptions,
    ) -> EchoOutput:
        """
        echo is a Nexus operation that always returns a synchronous result.
        """
        self.db_client.execute("<some query>")
        return EchoOutput(message=input.message)

    # ----------------------------------------------------------------------------------
    #
    # Asynchronous Nexus operations defined via convenience decorators.

    @temporalio.nexus.workflow_operation
    async def hello(
        self,
        input: HelloInput,
        options: nexusrpc.handler.OperationOptions,
    ) -> AsyncWorkflowOperationResult[HelloOutput]:
        """
        hello is a Nexus operation that always returns an asynchronous result.
        It is backed by a Temporal workflow.
        """
        return await temporalio.nexus.handler.start_workflow(HelloWorkflow.run, input)

    # @temporalio.nexus.update_operation
    # async def hello2(self, input: HelloInput) -> AsyncOperationResult:
    #     return await temporalio.nexus.handler.start_update(
    #         HelloWorkflow.my_update, input
    #     )

    # @temporalio.nexus.activity_operation
    # async def hello3(self, input: HelloInput) -> AsyncOperationResult:
    #     return await temporalio.nexus.handler.start_activity(hello_activity, input)

    # ----------------------------------------------------------------------------------
    #
    # Nexus operations defined using OperationHandler


class HelloOperation:
    def __init__(self, service: "MyNexusService"):
        self.service = service

    async def start(
        self, input: HelloInput, options: nexusrpc.handler.OperationOptions
    ) -> Union[HelloOutput, AsyncWorkflowOperationResult[HelloOutput]]:
        self.service.db_client.execute("<some query>")
        # Request-time dispatch to sync or async handling
        if len(input.name) % 2:
            return HelloOutput(message=f"Hello {input.name}! [from sync operation]")
        else:
            return await temporalio.nexus.handler.start_workflow(
                HelloWorkflow.run, input
            )

    async def cancel(self) -> None:
        raise NotImplementedError

    async def fetch_info(self) -> nexusrpc.handler.OperationInfo:
        raise NotImplementedError
