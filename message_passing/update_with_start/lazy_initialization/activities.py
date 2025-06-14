import asyncio
from dataclasses import dataclass
from typing import Optional

from temporalio import activity


@dataclass
class ShoppingCartItem:
    sku: str
    quantity: int


@activity.defn
async def get_price(item: ShoppingCartItem) -> Optional[int]:
    await asyncio.sleep(0.1)
    price = None if item.sku == "sku-456" else 599
    if price is None:
        return None
    return price * item.quantity
