"""Ticket triage workflow with Arize tracing via OpenTelemetry.

The workflow runs in the standard sandbox. With ``OpenTelemetryPlugin`` on the
client, plain OpenTelemetry APIs work in workflow code: the ``triage`` span
below gets a deterministic span ID and is never re-exported on replay.
"""

from datetime import timedelta
from typing import Optional

from temporalio import workflow
from temporalio.common import RetryPolicy

TASK_QUEUE = "arize-ticket-triage-task-queue"

# Bounded retries so a misconfigured endpoint fails fast. Each attempt records
# its own RunActivity span (see --fail-first-attempt on the worker).
LLM_RETRY_POLICY = RetryPolicy(
    maximum_attempts=3, initial_interval=timedelta(seconds=1)
)

with workflow.unsafe.imports_passed_through():
    from openinference.semconv.trace import (
        OpenInferenceSpanKindValues,
        SpanAttributes,
    )
    from opentelemetry import trace

    from ticket_triage.activities import (
        ApprovalDecision,
        Classification,
        DraftReplyInput,
        Ticket,
        TriageResult,
        classify_ticket,
        draft_reply,
        lookup_account,
    )


# @@@SNIPSTART python-arize-tracing-workflow
@workflow.defn
class TicketTriageWorkflow:
    def __init__(self) -> None:
        self._approval: Optional[ApprovalDecision] = None

    @workflow.run
    async def run(self, ticket: Ticket) -> TriageResult:
        # A custom span grouping the two triage activities; replay-safe under
        # the plugin. The OpenInference kind tells Arize how to render it.
        with trace.get_tracer(__name__).start_as_current_span(
            "triage",
            attributes={
                SpanAttributes.OPENINFERENCE_SPAN_KIND: OpenInferenceSpanKindValues.CHAIN.value
            },
        ) as span:
            classification: Classification = await workflow.execute_activity(
                classify_ticket,
                ticket,
                start_to_close_timeout=timedelta(seconds=60),
                # Heartbeats let Temporal notice a worker that died mid-attempt.
                heartbeat_timeout=timedelta(seconds=10),
                retry_policy=LLM_RETRY_POLICY,
            )
            account = await workflow.execute_activity(
                lookup_account,
                ticket.customer_email,
                start_to_close_timeout=timedelta(seconds=10),
            )
            span.set_attribute("triage.category", classification.category)
            span.set_attribute("triage.priority", classification.priority)

        # Wait for a human approval, delivered as a workflow update.
        await workflow.wait_condition(lambda: self._approval is not None)
        approval = self._approval
        assert approval is not None
        if not approval.approved:
            return TriageResult(status="declined", classification=classification)

        reply = await workflow.execute_activity(
            draft_reply,
            DraftReplyInput(
                ticket=ticket, classification=classification, account=account
            ),
            start_to_close_timeout=timedelta(seconds=60),
            retry_policy=LLM_RETRY_POLICY,
        )
        return TriageResult(
            status="replied", classification=classification, reply=reply
        )

    @workflow.update
    async def approve(self, decision: ApprovalDecision) -> str:
        self._approval = decision
        return "approved" if decision.approved else "declined"

    @approve.validator
    def approve_validator(self, decision: ApprovalDecision) -> None:
        if decision.approved and not decision.reviewer:
            raise ValueError("approval requires a reviewer")


# @@@SNIPEND
