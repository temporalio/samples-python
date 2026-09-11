"""Ticket triage with the OpenAI Agents SDK, traced to Arize via OpenTelemetry.

The agent loop runs inside the workflow, durably. Through ``OpenAIAgentsPlugin``
every model call runs as a Temporal activity, and ``activity_as_tool`` exposes
the ``lookup_account`` activity to the agent as a tool. With
``use_otel_instrumentation=True`` the plugin turns the Agents SDK trace into
OpenInference spans (AGENT, LLM, TOOL, and CHAIN for the Temporal operations)
on Temporal's replay-safe tracer provider, so Arize renders the agent natively
and replay never duplicates a span.
"""

from dataclasses import dataclass
from datetime import timedelta
from typing import Optional

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from agents import Agent, Runner
    from temporalio.contrib import openai_agents as temporal_agents

    from arize_tracing.ticket_triage.activities import (
        ApprovalDecision,
        Classification,
        Ticket,
        TriageResult,
        lookup_account,
        parse_classification,
    )


@dataclass
class AgentTicketRequest:
    ticket: Ticket
    # The model name is a workflow input rather than an environment lookup in
    # workflow code, which keeps the workflow deterministic.
    model: str = "gpt-4o-mini"


TRIAGE_INSTRUCTIONS = (
    "You are a support ticket triage agent. First look up the customer's account "
    "with the lookup_account tool, then classify the ticket. Respond with ONLY a "
    'JSON object like {"category": "billing|bug|how-to|other", '
    '"priority": "low|normal|high"}.'
)

REPLY_INSTRUCTIONS = (
    "You are a support agent. Draft a short (under 120 words), friendly reply to "
    "the customer's ticket, using the classification you are given."
)


# @@@SNIPSTART python-arize-tracing-agents-workflow
@workflow.defn
class TicketTriageAgentsWorkflow:
    def __init__(self) -> None:
        self._approval: Optional[ApprovalDecision] = None

    @workflow.run
    async def run(self, request: AgentTicketRequest) -> TriageResult:
        ticket = request.ticket
        triage_agent = Agent(
            name="Triage agent",
            model=request.model,
            instructions=TRIAGE_INSTRUCTIONS,
            tools=[
                # A Temporal activity as an agent tool: Arize shows a TOOL span
                # wrapping the activity's own Temporal spans.
                temporal_agents.workflow.activity_as_tool(
                    lookup_account, start_to_close_timeout=timedelta(seconds=10)
                )
            ],
        )
        triage = await Runner.run(
            triage_agent,
            input=(
                f"Ticket from {ticket.customer_email}\n"
                f"Subject: {ticket.subject}\n\n{ticket.body}"
            ),
        )
        classification: Classification = parse_classification(str(triage.final_output))

        # Wait for a human approval, delivered as a workflow update.
        await workflow.wait_condition(lambda: self._approval is not None)
        approval = self._approval
        assert approval is not None
        if not approval.approved:
            return TriageResult(status="declined", classification=classification)

        reply_agent = Agent(
            name="Reply agent", model=request.model, instructions=REPLY_INSTRUCTIONS
        )
        reply = await Runner.run(
            reply_agent,
            input=(
                f"Ticket: {ticket.subject}\n{ticket.body}\n\n"
                f"Category: {classification.category}, "
                f"priority: {classification.priority}"
            ),
        )
        return TriageResult(
            status="replied",
            classification=classification,
            reply=str(reply.final_output),
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
