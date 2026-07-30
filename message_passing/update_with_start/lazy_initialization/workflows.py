from dataclasses import dataclass
from datetime import timedelta
from typing import List, Tuple

from temporalio import workflow
from temporalio.exceptions import ApplicationError

with workflow.unsafe.imports_passed_through():
    from message_passing.update_with_start.lazy_initialization.activities import (
        ShoppingCartItem,
        get_price,
    )


@dataclass
class FinalizedOrder:
    id: str
    items: List[Tuple[ShoppingCartItem, int]]
    total: int


@workflow.defn
class ShoppingCartWorkflow:
    def __init__(self):
        self.items: List[Tuple[ShoppingCartItem, int]] = []
        self.order_submitted = False

    @workflow.run
    async def run(self) -> FinalizedOrder:
        await workflow.wait_condition(
            lambda: workflow.all_handlers_finished() and self.order_submitted
        )
        return FinalizedOrder(
            id=workflow.info().workflow_id,
            items=self.items,
            total=sum(price for _, price in self.items),
        )

    @workflow.update
    async def add_item(self, item: ShoppingCartItem) -> int:
        price = await workflow.execute_activity(
            get_price, item, start_to_close_timeout=timedelta(seconds=10)
        )
        if price is None:
            raise ApplicationError(
                f"Item unavailable: {item}",
                type="ItemUnavailableError",
            )
        self.items.append((item, price))

        return sum(price for _, price in self.items)

    @add_item.validator
    def validate_add_item(self, item: ShoppingCartItem) -> None:
        if self.order_submitted:
            raise ApplicationError("Order already submitted")

    @workflow.signal
    def checkout(self):
        self.order_submitted = True
