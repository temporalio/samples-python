import asyncio
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from temporalio import activity


@dataclass
class ShoppingCartItem:
    sku: str
    quantity: int


@activity.defn
async def get_price(item: ShoppingCartItem) -> Optional[str]:
    await asyncio.sleep(0.1)
    price = None if item.sku == "sku-456" else Decimal("5.99")
    if price is None:
        return None
    return str(price * item.quantity)
