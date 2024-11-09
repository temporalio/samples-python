import os
from datetime import timedelta
from typing import Optional, TypeVar

from opentelemetry import trace
from temporalio import common
from temporalio.api.common.v1 import WorkflowExecution
from temporalio.api.update.v1 import UpdateRef
from temporalio.api.workflowservice.v1 import PollWorkflowExecutionUpdateRequest
from temporalio.client import Client, WorkflowHandle
from temporalio.service import RPCError, RPCStatusCode
from temporalio.types import MethodAsyncNoParam

from dan.constants import TASK_QUEUE, WORKFLOW_ID
from dan.utils import connect
from dan.utils.otel import create_tracer_provider

S = TypeVar("S")
R = TypeVar("R")


async def start_workflow(
    run: MethodAsyncNoParam[S, R],
    id: Optional[str] = None,
    id_conflict_policy=common.WorkflowIDConflictPolicy.TERMINATE_EXISTING,
    client: Optional[Client] = None,
    **kwargs,
) -> WorkflowHandle[S, R]:
    if os.getenv("TRACING"):
        print("🩻")
        trace.set_tracer_provider(create_tracer_provider("Client"))
    if not client:
        client = await connect()
    return await client.start_workflow(
        run,
        id=id or WORKFLOW_ID,
        task_queue=TASK_QUEUE,
        id_conflict_policy=id_conflict_policy,
        task_timeout=timedelta(minutes=77),
        **kwargs,
    )


async def update_has_been_admitted(
    client: Client, workflow_id: str, update_id: str
) -> bool:
    try:
        await client.workflow_service.poll_workflow_execution_update(
            PollWorkflowExecutionUpdateRequest(
                namespace=client.namespace,
                update_ref=UpdateRef(
                    workflow_execution=WorkflowExecution(workflow_id=workflow_id),
                    update_id=update_id,
                ),
            )
        )
        return True
    except RPCError as err:
        if err.status != RPCStatusCode.NOT_FOUND:
            raise
        return False
