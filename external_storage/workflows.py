from dataclasses import dataclass
from datetime import timedelta
from typing import List

from temporalio import activity, workflow

WAREHOUSE_STATE = "TX"  # fulfillment center state used to estimate delivery


@dataclass
class Address:
    street: str
    city: str
    state: str
    zip_code: str
    country: str


@dataclass
class Customer:
    id: str
    name: str
    email: str
    address: Address


@dataclass
class OrderItem:
    sku: str
    name: str
    description: str
    quantity: int
    unit_price_usd: float
    weight_kg: float


@dataclass
class Order:
    id: str
    customer: Customer
    items: List[OrderItem]
    total_weight_kg: float
    shipping_notes: str


@dataclass
class ProcessedOrder:
    id: str
    customer_id: str
    destination_city: str
    destination_state: str
    total_weight_kg: float
    shipping_cost_usd: float
    estimated_delivery_days: int


@dataclass
class OrderBatchRequest:
    batch_id: str
    order_count: int


@dataclass
class BatchSummary:
    batch_id: str
    order_count: int
    total_shipping_cost_usd: float
    total_weight_kg: float
    avg_delivery_days: float


@activity.defn
async def fetch_orders(request: OrderBatchRequest) -> List[Order]:
    # Lazy import keeps the data-generation code out of the workflow module's
    # top-level imports and avoids a circular import with _sample_data.
    from external_storage._sample_data import generate_orders

    return generate_orders(request.batch_id, request.order_count)


@activity.defn
async def process_orders(orders: List[Order]) -> List[ProcessedOrder]:
    results: List[ProcessedOrder] = []
    for order in orders:
        cost = round(2.50 + 1.20 * order.total_weight_kg, 2)
        days = 2 if order.customer.address.state == WAREHOUSE_STATE else 5
        results.append(
            ProcessedOrder(
                id=order.id,
                customer_id=order.customer.id,
                destination_city=order.customer.address.city,
                destination_state=order.customer.address.state,
                total_weight_kg=order.total_weight_kg,
                shipping_cost_usd=cost,
                estimated_delivery_days=days,
            )
        )
    return results


@workflow.defn
class ProcessOrderBatchWorkflow:
    @workflow.run
    async def run(self, request: OrderBatchRequest) -> BatchSummary:
        orders = await workflow.execute_activity(
            fetch_orders,
            request,
            start_to_close_timeout=timedelta(minutes=5),
        )
        processed = await workflow.execute_activity(
            process_orders,
            orders,
            start_to_close_timeout=timedelta(minutes=5),
        )
        total_cost = sum(p.shipping_cost_usd for p in processed)
        total_weight = sum(p.total_weight_kg for p in processed)
        avg_days = (
            sum(p.estimated_delivery_days for p in processed) / len(processed)
            if processed
            else 0.0
        )
        return BatchSummary(
            batch_id=request.batch_id,
            order_count=len(processed),
            total_shipping_cost_usd=round(total_cost, 2),
            total_weight_kg=round(total_weight, 2),
            avg_delivery_days=round(avg_days, 1),
        )
