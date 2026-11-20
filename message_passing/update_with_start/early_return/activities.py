import asyncio
import uuid
from dataclasses import dataclass

from temporalio import activity


@dataclass(frozen=True)
class PaymentDetails:
    amount: int


@dataclass(frozen=True)
class PaymentAuthorization:
    id: str
    amount: int


@activity.defn
async def authorize_payment(details: PaymentDetails) -> PaymentAuthorization:
    await asyncio.sleep(0.5)
    authorization = PaymentAuthorization(
        id=f"authorization-{uuid.uuid4()}",
        amount=details.amount,
    )
    activity.logger.info("Payment authorized: %s", authorization.id)
    return authorization


@activity.defn
async def capture_payment(authorization: PaymentAuthorization) -> None:
    await asyncio.sleep(5)
    activity.logger.info("Payment captured: %s", authorization.id)
