"""
Notes:

Sync operations:
---------------
Implementations are free to make arbitrary network calls, or perform CPU-bound
computations such as this one. Total execution duration must not exceed 10s. To
perform Temporal client calls such as signaling/querying/listing workflows, use
self.client.


Workflow operations:
---------------------
The task queue defaults to the task queue being used by the Nexus worker.
"""

from __future__ import annotations

import nexusrpc.handler
import temporalio.common
import temporalio.nexus.handler

from hello_nexus.handler.dbclient import MyDBClient
from hello_nexus.handler.workflows import HelloWorkflow
from hello_nexus.service import interface
from hello_nexus.service.interface import (
    EchoInput,
    EchoOutput,
    HelloInput,
    HelloOutput,
)


# Inheriting from the protocol here is optional. Users who do it will get the
# operation definition itself type-checked in situ against the interface (*).
# Call-sites using instances of the operation are always type-checked.
#
# (*) However, in VSCode/Pyright this is done only when type-checking is set to
# 'strict'.
class EchoOperation(nexusrpc.handler.Operation[EchoInput, EchoOutput]):
    def __init__(self, service: MyNexusService):
        self.service = service

    async def start(
        self, input: EchoInput, options: nexusrpc.handler.StartOperationOptions
    ) -> EchoOutput:
        return EchoOutput(message=f"Echo {input.message}!")

    async def cancel(
        self, token: str, options: nexusrpc.handler.CancelOperationOptions
    ) -> None:
        raise NotImplementedError

    async def fetch_info(
        self, token: str, options: nexusrpc.handler.FetchOperationInfoOptions
    ) -> nexusrpc.handler.OperationInfo:
        raise NotImplementedError

    async def fetch_result(
        self, token: str, options: nexusrpc.handler.FetchOperationResultOptions
    ) -> EchoOutput:
        raise NotImplementedError


# Inheriting from the protocol here is optional. Users who do it will get the
# operation definition itself type-checked in situ against the interface (*).
# Call-sites using instances of the operation are always type-checked.
#
# (*) However, in VSCode/Pyright this is done only when type-checking is set to
# 'strict'.
class HelloOperation:  # (nexusrpc.handler.Operation[HelloInput, HelloOutput]):
    def __init__(self, service: "MyNexusService"):
        self.service = service

    async def start(
        self, input: HelloInput, options: nexusrpc.handler.StartOperationOptions
    ) -> temporalio.nexus.handler.StartWorkflowOperationResult[HelloOutput]:
        self.service.db_client.execute("<some query>")
        workflow_id = "default-workflow-id"
        return await temporalio.nexus.handler.start_workflow(
            HelloWorkflow.run,
            input,
            id=workflow_id,
            options=options,
        )

    async def cancel(
        self, token: str, options: nexusrpc.handler.CancelOperationOptions
    ) -> None:
        return await temporalio.nexus.handler.cancel_workflow(token, options)

    async def fetch_info(
        self, token: str, options: nexusrpc.handler.FetchOperationInfoOptions
    ) -> nexusrpc.handler.OperationInfo:
        return await temporalio.nexus.handler.fetch_workflow_info(token, options)

    async def fetch_result(
        self, token: str, options: nexusrpc.handler.FetchOperationResultOptions
    ) -> HelloOutput:
        return await temporalio.nexus.handler.fetch_workflow_result(token, options)


class EchoOperation3(nexusrpc.handler.AbstractOperation[EchoInput, EchoOutput]):
    async def start(
        self, input: EchoInput, options: nexusrpc.handler.StartOperationOptions
    ) -> EchoOutput:
        return EchoOutput(message=f"Echo {input.message}! [from base class variant]")


@nexusrpc.handler.service(interface=interface.MyNexusService)
class MyNexusService:
    def __init__(self, db_client: MyDBClient):
        # An example of something that might be held by the service instance.
        self.db_client = db_client

    # --------------------------------------------------------------------------
    # Operations defined by explicitly implementing the Operation interface.
    #

    @nexusrpc.handler.operation
    def echo(self) -> nexusrpc.handler.Operation[EchoInput, EchoOutput]:
        return EchoOperation(self)

    @nexusrpc.handler.operation
    def hello(self) -> nexusrpc.handler.Operation[HelloInput, HelloOutput]:
        return HelloOperation(self)

    @nexusrpc.handler.operation
    def echo3(self) -> nexusrpc.handler.Operation[EchoInput, EchoOutput]:
        return EchoOperation3()

    # --------------------------------------------------------------------------
    # Operations defined by providing the start method only, using the
    # "shorthand" decorators.
    #
    # Note that a start method defined this way has access to the service
    # instance, but not to the operation instance (users who need the latter
    # should implement the Operation interface directly).

    @nexusrpc.handler.sync_operation
    async def echo2(
        self, input: EchoInput, _: nexusrpc.handler.StartOperationOptions
    ) -> EchoOutput:
        return EchoOutput(message=f"Echo {input.message} [via shorthand]!")

    # --------------------------------------------------------------------------
    # Operations defined by providing the start method only, using the
    # "shorthand" decorators.
    #
    # Note that a start method defined this way has access to the service
    # instance, but not to the operation instance (users who need the latter
    # should implement the Operation interface directly).

    @temporalio.nexus.handler.workflow_operation
    async def hello2(
        self, input: HelloInput, options: nexusrpc.handler.StartOperationOptions
    ) -> temporalio.nexus.handler.StartWorkflowOperationResult[HelloOutput]:
        self.db_client.execute("<some query>")
        workflow_id = "default-workflow-id"
        input.name += " [via shorthand]"
        return await temporalio.nexus.handler.start_workflow(
            HelloWorkflow.run,
            input,
            id=workflow_id,
            options=options,
        )


if __name__ == "__main__":
    # Check run-time type annotations resulting from the decorators.
    service = MyNexusService(MyDBClient())
    print("echo:", temporalio.common._type_hints_from_func(service.echo2().start))
    print(
        "hello:", temporalio.common._type_hints_from_func(service.hello2().fetch_result)
    )
