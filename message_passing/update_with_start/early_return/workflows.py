from datetime import timedelta
from typing import Optional

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from message_passing.update_with_start.early_return.activities import (
        PaymentAuthorization,
        PaymentDetails,
        authorize_payment,
        capture_payment,
    )


@workflow.defn
class PaymentWorkflow:
    def __init__(self) -> None:
        self.authorization: Optional[PaymentAuthorization] = None

    @workflow.run
    async def run(self, details: PaymentDetails) -> PaymentAuthorization:
        self.authorization = await workflow.execute_activity(
            authorize_payment,
            details,
            start_to_close_timeout=timedelta(seconds=10),
        )

        await workflow.execute_activity(
            capture_payment,
            self.authorization,
            start_to_close_timeout=timedelta(seconds=30),
        )
        return self.authorization

    @workflow.update
    async def wait_until_authorized(self) -> PaymentAuthorization:
        await workflow.wait_condition(lambda: self.authorization is not None)
        assert self.authorization is not None
        return self.authorization
