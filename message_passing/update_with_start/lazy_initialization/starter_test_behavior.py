import asyncio
import uuid
from typing import Tuple

from temporalio import common
from temporalio.client import (
    Client,
    WithStartWorkflowOperation,
    WorkflowHandle,
)

from message_passing.update_with_start.lazy_initialization import TASK_QUEUE
from message_passing.update_with_start.lazy_initialization.workflows import (
    ShoppingCartItem,
    ShoppingCartWorkflow,
)


def key(handle: WorkflowHandle) -> Tuple[str, str]:
    assert handle.first_execution_run_id
    return handle.id, handle.first_execution_run_id[:12]


async def complete_workflow(wid: str, upd_id: str):
    temporal_client = await Client.connect("localhost:7233")

    # First create and complete a workflow
    handle = await temporal_client.start_workflow(
        ShoppingCartWorkflow.run,
        id=wid,
        task_queue=TASK_QUEUE,
    )
    print(f"🟢 Workflow started: {key(handle)}")

    # Add an item and then checkout to complete the workflow
    total = await handle.execute_update(
        ShoppingCartWorkflow.add_item,
        ShoppingCartItem(sku="test-item", quantity=1),
        id=upd_id,
    )
    print(f"🟢 Workflow updated, total: {total}")
    await handle.signal(ShoppingCartWorkflow.checkout)

    # Wait for workflow to complete
    final_order = await handle.result()
    assert handle.first_execution_run_id
    print(f"Workflow completed: {key(handle)}, total: {final_order.total}")


async def test_uws_completed_workflow_allow_dups():
    """
    Test the behavior when a workflow is closed with 'completed' status
    and we try to use updateWithStart on it.
    """
    temporal_client = await Client.connect("localhost:7233")
    wf_id = f"wf-{str(uuid.uuid4())}"
    upd_id = f"upd-{str(uuid.uuid4())}"

    await complete_workflow(wf_id, upd_id)

    # Now try updateWithStart on the completed workflow
    start_op = WithStartWorkflowOperation(
        ShoppingCartWorkflow.run,
        id=wf_id,
        id_reuse_policy=common.WorkflowIDReusePolicy.ALLOW_DUPLICATE,
        id_conflict_policy=common.WorkflowIDConflictPolicy.USE_EXISTING,
        task_queue=TASK_QUEUE,
    )

    try:
        print(
            "Attempting updateWithStart with ALLOW_DUPLICATE on completed workflow..."
        )
        total = await temporal_client.execute_update_with_start_workflow(
            ShoppingCartWorkflow.add_item,
            ShoppingCartItem(sku="another-item", quantity=1),
            start_workflow_operation=start_op,
            id=upd_id,
        )
        print(f"🟢 UwS succeeded with ALLOW_DUPLICATE, total: {total}")
    except Exception as e:
        print(
            f"🔴 UwS failed with ALLOW_DUPLICATE: Error - {type(e).__name__}: {str(e)}"
        )
    try:
        workflow_handle = await start_op.workflow_handle()
        print(f"🟢 workflow handle: {key(workflow_handle)}")
    except Exception as e:
        print(f"🔴 Error getting workflow handle: {e}")


async def test_uws_completed_workflow_reject_dups():
    """
    Test the behavior when a workflow is closed with 'completed' status
    and we try to use updateWithStart on it.
    """
    temporal_client = await Client.connect("localhost:7233")
    wf_id = f"wf-{str(uuid.uuid4())}"
    upd_id = f"upd-{str(uuid.uuid4())}"

    await complete_workflow(wf_id, upd_id)

    start_op = WithStartWorkflowOperation(
        ShoppingCartWorkflow.run,
        id=wf_id,
        id_reuse_policy=common.WorkflowIDReusePolicy.REJECT_DUPLICATE,
        id_conflict_policy=common.WorkflowIDConflictPolicy.FAIL,
        task_queue=TASK_QUEUE,
    )

    try:
        print(
            "Attempting updateWithStart with REJECT_DUPLICATE on completed workflow..."
        )
        total = await temporal_client.execute_update_with_start_workflow(
            ShoppingCartWorkflow.add_item,
            ShoppingCartItem(sku="another-item", quantity=1),
            start_workflow_operation=start_op,
        )
        print(f"🟢 UwS succeeded with REJECT_DUPLICATE, total: {total}")
    except Exception as e:
        print(
            f"🔴 UwS failed with REJECT_DUPLICATE: Error - {type(e).__name__}: {str(e)}"
        )
    try:
        workflow_handle = await start_op.workflow_handle()
        print(f"🟢 workflow handle: {key(workflow_handle)}")
    except Exception as e:
        print(f"🔴 Error getting workflow handle: {e}")


async def main():
    await test_uws_completed_workflow_allow_dups()
    print("\n\n\n\n")
    await test_uws_completed_workflow_reject_dups()


if __name__ == "__main__":
    asyncio.run(main())
