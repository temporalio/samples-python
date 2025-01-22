import asyncio
import os
import time
from datetime import timedelta
from typing import Awaitable, Callable, Optional, TypeVar

from opentelemetry import trace
from temporalio import common
from temporalio.api.common.v1 import WorkflowExecution
from temporalio.api.update.v1 import UpdateRef
from temporalio.api.workflowservice.v1 import PollWorkflowExecutionUpdateRequest
from temporalio.client import Client, WorkflowHandle
from temporalio.service import RPCError, RPCStatusCode
from temporalio.types import MethodAsyncNoParam
from temporalio.workflow import UpdateMethodMultiParam

from dan.constants import TASK_QUEUE, WORKFLOW_ID
from dan.utils import connect
from dan.utils.otel import create_tracer_provider

R = TypeVar("R")
S = TypeVar("S")
T = TypeVar("T")


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


# The update utilities below are copied from
# https://github.com/temporalio/sdk-python/blob/main/tests/helpers/__init__.py


async def admitted_update_task(
    client: Client,
    handle: WorkflowHandle,
    update_method: UpdateMethodMultiParam,
    id: str,
    **kwargs,
) -> asyncio.Task:
    """
    Return an asyncio.Task for an update after waiting for it to be admitted.
    """
    update_task = asyncio.create_task(
        handle.execute_update(update_method, id=id, **kwargs)
    )
    await assert_eq_eventually(
        True,
        lambda: update_has_been_admitted(client, handle.id, id),
    )
    return update_task


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


async def assert_eq_eventually(
    expected: T,
    fn: Callable[[], Awaitable[T]],
    *,
    timeout: timedelta = timedelta(seconds=10),
    interval: timedelta = timedelta(milliseconds=200),
) -> None:
    start_sec = time.monotonic()
    last_value = None
    while timedelta(seconds=time.monotonic() - start_sec) < timeout:
        last_value = await fn()
        if expected == last_value:
            return
        await asyncio.sleep(interval.total_seconds())
    assert (
        expected == last_value
    ), f"timed out waiting for equal, asserted against last value of {last_value}"
