from asyncio import Future
from dataclasses import dataclass
from typing import Literal
from uuid import uuid4

from temporalio import workflow

#
# LockService (lazy init)
# A workflow acts as an always-available service and supports an `acquire_lock` update.
#


@dataclass
class Lock:
    token: str


@workflow.defn
class LockService:
    @workflow.run
    async def run(self) -> None:
        await Future()

    @workflow.update
    async def acquire_lock(self) -> Lock:
        # TODO: implement lock service sample
        token = str(uuid4())
        return Lock(token)


#
# FinancialTransaction (early return)
# The workflow is a multi-stage financial transaction and supports a low-latency `get_confirmation` update.
#


@dataclass
class TransactionRequest:
    amount: float


@dataclass
class TransactionReport:
    id: str
    final_amount: float
    status: Literal["complete", "failed"]


@dataclass
class TransactionConfirmation:
    id: str
    status: Literal["confirmed"]


@workflow.defn
class TransactionWorkflow:
    def __init__(self):
        self.ready_to_issue_final_report = False

    @workflow.run
    async def run(self, request: TransactionRequest) -> TransactionReport:
        await workflow.wait_condition(lambda: self.ready_to_issue_final_report)
        return TransactionReport(
            id=workflow.info().workflow_id,
            status="complete",
            final_amount=request.amount * 0.97,
        )

    @workflow.update
    async def get_confirmation(self) -> TransactionConfirmation:
        self.ready_to_issue_final_report = True
        return TransactionConfirmation(
            id=workflow.info().workflow_id,
            status="confirmed",
        )
