"""Companion HITL workflow.

The triage agent's request_human_approval tool calls signal_with_start
against a deterministic ID per alert group. This workflow stores the latest
agent request, exposes it as a query, and returns the operator's decision.

Same shape as the TypeScript reference's approval workflow (workers/typescript/
workflows/approval.ts) — deterministic ID, request signal, decision signal,
pending-approval query, two condition() blocks.
"""
from __future__ import annotations

from temporalio import workflow

from triage_types import ApprovalRequest, ApprovalResponse


@workflow.defn(name="approvalWorkflow")
class ApprovalWorkflow:
    def __init__(self) -> None:
        self._request: ApprovalRequest | None = None
        self._response: ApprovalResponse | None = None

    @workflow.run
    async def run(self, _key: str) -> ApprovalResponse:
        # Block until the agent signals a request AND the operator responds.
        await workflow.wait_condition(lambda: self._request is not None)
        await workflow.wait_condition(lambda: self._response is not None)
        assert self._response is not None
        return self._response

    @workflow.signal(name="approval-request")
    def request(self, req: ApprovalRequest) -> None:
        # LLM retry: re-attached signals overwrite the request. Operator only
        # ever sees the latest version, since the agent may refine its ask
        # across retries.
        self._request = req

    @workflow.signal(name="approval-decision")
    def decide(self, res: ApprovalResponse) -> None:
        self._response = res

    @workflow.query(name="pending-approval")
    def pending(self) -> ApprovalRequest | None:
        return self._request
