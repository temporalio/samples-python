import asyncio
import uuid
from typing import Optional, Tuple

from temporalio import common
from temporalio.client import (
    Client,
    WithStartWorkflowOperation,
    WorkflowHandle,
    WorkflowUpdateFailedError,
)
from temporalio.envconfig import ClientConfig
from temporalio.exceptions import ApplicationError

from message_passing.update_with_start.lazy_initialization import TASK_QUEUE
from message_passing.update_with_start.lazy_initialization.workflows import (
    ShoppingCartItem,
    ShoppingCartWorkflow,
)
from util import get_temporal_config_path


async def handle_add_item_request(
    session_id: str, item_id: str, quantity: int, temporal_client: Client
) -> Tuple[Optional[int], WorkflowHandle]:
    """
    Handle a client request to add an item to the shopping cart. The user is not logged in, but a session ID is
    available from a cookie, and we use this as the cart ID. The Temporal client was created at service-start
    time and is shared by all request handlers.

    A Workflow Type exists that can be used to represent a shopping cart. The method uses update-with-start to
    add an item to the shopping cart, creating the cart if it doesn't already exist.

    Note that the workflow handle is available, even if the Update fails.
    """
    cart_id = f"cart-{session_id}"
    start_op = WithStartWorkflowOperation(
        ShoppingCartWorkflow.run,
        id=cart_id,
        id_conflict_policy=common.WorkflowIDConflictPolicy.USE_EXISTING,
        task_queue=TASK_QUEUE,
    )
    try:
        price = await temporal_client.execute_update_with_start_workflow(
            ShoppingCartWorkflow.add_item,
            ShoppingCartItem(sku=item_id, quantity=quantity),
            start_workflow_operation=start_op,
        )
    except WorkflowUpdateFailedError as err:
        if (
            isinstance(err.cause, ApplicationError)
            and err.cause.type == "ItemUnavailableError"
        ):
            price = None
        else:
            raise err

    workflow_handle = await start_op.workflow_handle()

    return price, workflow_handle


async def main():
    print("🛒")
    session_id = f"session-{uuid.uuid4()}"
    config = ClientConfig.load_client_connect_config(
        config_file=str(get_temporal_config_path())
    )

    client = await Client.connect(**config)
    subtotal_1, _ = await handle_add_item_request(session_id, "sku-123", 1, client)
    subtotal_2, wf_handle = await handle_add_item_request(
        session_id, "sku-456", 1, client
    )
    print(f"subtotals were, {[subtotal_1, subtotal_2]}")
    await wf_handle.signal(ShoppingCartWorkflow.checkout)
    final_order = await wf_handle.result()
    print(f"final order: {final_order}")


if __name__ == "__main__":
    asyncio.run(main())
