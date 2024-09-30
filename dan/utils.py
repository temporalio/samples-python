import asyncio
import traceback
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from typing import Optional, TypeVar

import rich
from temporalio import common, workflow
from temporalio.api.common.v1 import WorkflowExecution
from temporalio.api.update.v1 import UpdateRef
from temporalio.api.workflowservice.v1 import PollWorkflowExecutionUpdateRequest
from temporalio.client import Client, WorkflowHandle
from temporalio.service import RPCError, RPCStatusCode
from temporalio.types import MethodAsyncNoParam

from dan.constants import NAMESPACE, TASK_QUEUE, WORKFLOW_ID

S = TypeVar("S")
R = TypeVar("R")


async def start_workflow(
    run: MethodAsyncNoParam[S, R],
    id: Optional[str] = None,
    id_reuse_policy=common.WorkflowIDReusePolicy.TERMINATE_IF_RUNNING,
    client: Optional[Client] = None,
    **kwargs,
) -> WorkflowHandle[S, R]:
    if not client:
        client = await Client.connect("localhost:7233", namespace=NAMESPACE)
    return await client.start_workflow(
        run,
        id=id or WORKFLOW_ID,
        task_queue=TASK_QUEUE,
        id_reuse_policy=id_reuse_policy,
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


def print(*args, **kwargs):
    with workflow.unsafe.imports_passed_through():
        rich.print(*args, **kwargs)


@contextmanager
def catch():
    try:
        yield
    except Exception as err:
        import pdb

        pdb.set_trace()
        print(err)


async def ainput(prompt: str = ""):
    with ThreadPoolExecutor(1, "ainput") as executor:
        return (
            await asyncio.get_event_loop().run_in_executor(executor, input, prompt)
        ).rstrip()


def print_stack():
    stack = traceback.extract_stack()
    formatted_stack = traceback.format_list(stack)
    for line in formatted_stack:
        print(line.strip())
