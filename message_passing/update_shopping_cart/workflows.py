from dataclasses import dataclass
from decimal import Decimal
from typing import Tuple

from temporalio import workflow
from temporalio.exceptions import ApplicationError

from message_passing.update_shopping_cart.activities import ShoppingCartItem, get_price


@dataclass
class FinalizedOrder:
    id: str
    items: list[Tuple[ShoppingCartItem, str]]
    total: str


@workflow.defn
class ShoppingCartWorkflow:
    def __init__(self):
        self.items: list[Tuple[ShoppingCartItem, Decimal]] = []
        self.order_submitted = False

    @workflow.run
    async def run(self) -> FinalizedOrder:
        await workflow.wait_condition(
            lambda: workflow.all_handlers_finished() and self.order_submitted
        )
        return FinalizedOrder(
            id=workflow.info().workflow_id,
            items=[(item, str(price)) for item, price in self.items],
            total=str(
                sum(item.quantity * price for item, price in self.items)
                or Decimal("0.00")
            ),
        )

    @workflow.update
    async def add_item(self, item: ShoppingCartItem) -> str:
        price = await get_price(item)
        if price is None:
            raise ApplicationError(
                f"Item unavailable: {item}",
            )
        self.items.append((item, Decimal(price)))
        return str(
            sum(item.quantity * price for item, price in self.items) or Decimal("0.00")
        )

    @workflow.signal
    def checkout(self):
        self.order_submitted = True
