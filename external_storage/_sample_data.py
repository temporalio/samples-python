"""Order data generation for the external_storage sample.

Produces payloads large enough to exceed the default 256 KiB ExternalStorage
threshold without hand-crafted catalogs of items, addresses, or notes — each
order is padded with random filler text in its item descriptions and shipping
notes. Calibrated so 100 orders serialize to roughly 300 KiB of JSON.
"""

import random
import string
from typing import List

from external_storage.workflows import Address, Customer, Order, OrderItem

_CITIES = [
    ("Houston", "TX"),
    ("Dallas", "TX"),
    ("Los Angeles", "CA"),
    ("San Francisco", "CA"),
    ("Denver", "CO"),
    ("Miami", "FL"),
    ("Chicago", "IL"),
    ("New York", "NY"),
    ("Seattle", "WA"),
    ("Atlanta", "GA"),
]

_ITEMS_PER_ORDER = 5
_ITEM_DESCRIPTION_CHARS = 500
_SHIPPING_NOTES_CHARS = 200


def _filler(rng: random.Random, n: int) -> str:
    return "".join(rng.choices(string.ascii_letters + " ", k=n))


def generate_orders(batch_id: str, count: int) -> List[Order]:
    return [_generate_order(batch_id, i) for i in range(1, count + 1)]


def _generate_order(batch_id: str, index: int) -> Order:
    rng = random.Random(f"{batch_id}-{index}")
    city, state = rng.choice(_CITIES)
    items = [
        OrderItem(
            sku=f"SKU-{rng.randint(10000, 99999)}",
            name=f"Product {rng.randint(1, 999)}",
            description=_filler(rng, _ITEM_DESCRIPTION_CHARS),
            quantity=rng.randint(1, 10),
            unit_price_usd=round(rng.uniform(10.0, 1000.0), 2),
            weight_kg=round(rng.uniform(0.5, 50.0), 2),
        )
        for _ in range(_ITEMS_PER_ORDER)
    ]
    return Order(
        id=f"ORD-{index:06d}",
        customer=Customer(
            id=f"CUST-{index:06d}",
            name=f"Customer {index}",
            email=f"customer{index}@example.com",
            address=Address(
                street=f"{rng.randint(100, 9999)} Main Street",
                city=city,
                state=state,
                zip_code=f"{rng.randint(10000, 99999)}",
                country="US",
            ),
        ),
        items=items,
        total_weight_kg=round(sum(i.weight_kg * i.quantity for i in items), 2),
        shipping_notes=_filler(rng, _SHIPPING_NOTES_CHARS),
    )
