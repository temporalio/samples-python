"""
This file demonstrates running a nexus service in the same namespace as the workflow that
is calling the nexus service, without specifying a separate service definition.
"""

from __future__ import annotations

import asyncio
import uuid
from typing import Optional

from nexusrpc.handler import service_handler
from temporalio import workflow
from temporalio.client import Client, WorkflowHandle
from temporalio.nexus import StartOperationContext
from temporalio.nexus.handler import workflow_run_operation_handler
from temporalio.worker import UnsandboxedWorkflowRunner, Worker
from temporalio.workflow import NexusClient

NAMESPACE = "my-namespace"
TASK_QUEUE = "my-task-queue"
NEXUS_ENDPOINT = "my-nexus-endpoint"

#
# Handler
#


@workflow.defn
class HandlerWorkflow:
    @workflow.run
    async def run(self, message: str) -> str:
        return f"Hello {message} from workflow run operation!"


# Here we define a nexus service by providing a service handler implementation without a
# service contract.
@service_handler
class MyNexusServiceHandler:
    # The nexus service has one operation. When using the workflow_run_operation_handler
    # decorator, your start method must return a WorkflowHandle directly, using the
    # temporalio.nexus.handler.start_workflow helper. (Temporal server takes care of
    # delivering the workflow result to the caller, using the Nexus RPC callback mechanism).
    @workflow_run_operation_handler
    async def my_workflow_run_operation(
        self, ctx: StartOperationContext, name: str
    ) -> WorkflowHandle[HandlerWorkflow, str]:
        return await ctx.client.start_workflow(
            HandlerWorkflow.run,
            name,
            id=str(uuid.uuid4()),
            task_queue=ctx.task_queue,
        )


#
# Caller
#


@workflow.defn
class CallerWorkflow:
    @workflow.run
    async def run(self, message: str) -> str:
        # Create the type-safe workflow nexus service client, and invoke the nexus
        # operation.
        #
        # Normally, the first argument to both these calls would reference a service
        # contract class, but they can also reference your service handler class, as here.

        nexus_client = NexusClient(MyNexusServiceHandler, endpoint=NEXUS_ENDPOINT)
        return await nexus_client.execute_operation(
            MyNexusServiceHandler.my_workflow_run_operation, message
        )


async def execute_caller_workflow(client: Optional[Client] = None) -> str:
    client = client or await Client.connect("localhost:7233", namespace=NAMESPACE)
    # Start a worker that polls for tasks for both the caller workflow and the nexus
    # service.
    async with Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[CallerWorkflow, HandlerWorkflow],
        nexus_service_handlers=[MyNexusServiceHandler()],
        # TODO(dan): isinstance(op, nexusrpc.contract.Operation) is failing under the
        # sandbox in temporalio/worker/_interceptor.py
        workflow_runner=UnsandboxedWorkflowRunner(),
    ):
        return await client.execute_workflow(
            CallerWorkflow.run,
            "world",
            id=str(uuid.uuid4()),
            task_queue=TASK_QUEUE,
        )


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    try:
        result = loop.run_until_complete(execute_caller_workflow())
        print(result)
    except KeyboardInterrupt:
        loop.run_until_complete(loop.shutdown_asyncgens())
