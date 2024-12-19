from decimal import Decimal

import pytest
from temporalio import common
from temporalio.client import (
    Client,
    WithStartWorkflowOperation,
)
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from message_passing.update_with_start.lazy_initialization.workflows import (
    ShoppingCartItem,
    ShoppingCartWorkflow,
    get_price,
)


async def test_shopping_cart_workflow(client: Client, env: WorkflowEnvironment):
    if env.supports_time_skipping:
        pytest.skip(
            "Java test server: https://github.com/temporalio/sdk-java/issues/1903"
        )
    async with Worker(
        client,
        task_queue="lazy-initialization-test",
        workflows=[ShoppingCartWorkflow],
        activities=[get_price],
    ):
        cart_id = "cart--session-1234"
        make_start_op = lambda: WithStartWorkflowOperation(
            ShoppingCartWorkflow.run,
            id=cart_id,
            id_conflict_policy=common.WorkflowIDConflictPolicy.USE_EXISTING,
            task_queue="lazy-initialization-test",
        )
        start_op_1 = make_start_op()
        price = Decimal(
            await client.execute_update_with_start_workflow(
                ShoppingCartWorkflow.add_item,
                ShoppingCartItem(sku="item-1", quantity=2),
                start_workflow_operation=start_op_1,
            )
        )

        assert price == Decimal("11.98")

        workflow_handle = await start_op_1.workflow_handle()

        start_op_2 = make_start_op()
        price = Decimal(
            await client.execute_update_with_start_workflow(
                ShoppingCartWorkflow.add_item,
                ShoppingCartItem(sku="item-2", quantity=1),
                start_workflow_operation=start_op_2,
            )
        )
        assert price == Decimal("17.97")

        workflow_handle = await start_op_2.workflow_handle()

        await workflow_handle.signal(ShoppingCartWorkflow.checkout)

        finalized_order = await workflow_handle.result()
        assert finalized_order.items == [
            (ShoppingCartItem(sku="item-1", quantity=2), "11.98"),
            (ShoppingCartItem(sku="item-2", quantity=1), "5.99"),
        ]
        assert finalized_order.total == "17.97"
