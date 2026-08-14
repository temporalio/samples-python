"""Activities for the ticket triage sample.

All LLM and I/O work happens here, in activities — never in workflow code.
The OpenAI client is instrumented process-wide (see ``telemetry.instrument_openai``),
so each API call below automatically emits a child span of the activity span,
which Langfuse displays as a GENERATION observation with model and token usage.
"""

import json
import os
from dataclasses import dataclass
from typing import Optional

from openai import AsyncOpenAI
from temporalio import activity


@dataclass
class Ticket:
    ticket_id: str
    customer_email: str
    subject: str
    body: str


@dataclass
class Classification:
    category: str
    priority: str


@dataclass
class AccountInfo:
    customer_email: str
    account_name: str
    plan: str


@dataclass
class DraftReplyInput:
    ticket: Ticket
    classification: Classification
    account: AccountInfo


@dataclass
class ApprovalDecision:
    approved: bool
    reviewer: str


@dataclass
class TriageResult:
    status: str
    classification: Classification
    reply: Optional[str] = None


CLASSIFY_PROMPT = (
    "You are a support ticket triage assistant. Classify the ticket and respond "
    'with ONLY a JSON object like {"category": "billing|bug|how-to|other", '
    '"priority": "low|normal|high"}.'
)

DRAFT_PROMPT = (
    "You are a support agent. Draft a short (under 120 words), friendly reply to "
    "the customer's ticket. Use the provided classification and account details."
)


def _openai_client() -> AsyncOpenAI:
    # Configuration comes from the environment, never from activity inputs
    # (activity inputs are recorded in workflow history and shown in the UI).
    # max_retries=0 disables the OpenAI client's built-in retries — Temporal's
    # activity retry policy owns retries, with full visibility in the UI.
    return AsyncOpenAI(
        base_url=os.environ.get("OPENAI_BASE_URL"),
        api_key=os.environ.get("OPENAI_API_KEY"),
        max_retries=0,
    )


def _parse_classification(text: str) -> Classification:
    try:
        data = json.loads(text[text.index("{") : text.rindex("}") + 1])
        return Classification(
            category=str(data.get("category", "other")).lower(),
            priority=str(data.get("priority", "normal")).lower(),
        )
    except ValueError:
        return Classification(category="other", priority="normal")


@activity.defn
async def classify_ticket(ticket: Ticket) -> Classification:
    response = await _openai_client().chat.completions.create(
        model=os.environ.get("MODEL_CLASSIFY", "gpt-4o-mini"),
        messages=[
            {"role": "system", "content": CLASSIFY_PROMPT},
            {"role": "user", "content": f"{ticket.subject}\n\n{ticket.body}"},
        ],
        timeout=30,
    )
    return _parse_classification(response.choices[0].message.content or "")


@activity.defn
async def lookup_account(customer_email: str) -> AccountInfo:
    # A deterministic, non-LLM activity: appears in Langfuse as a plain SPAN
    # observation alongside the GENERATION observations from the LLM activities.
    known_accounts = {
        "ada@acme.example": AccountInfo(
            customer_email="ada@acme.example",
            account_name="Acme Corp",
            plan="enterprise",
        ),
    }
    return known_accounts.get(
        customer_email,
        AccountInfo(customer_email=customer_email, account_name="Unknown", plan="free"),
    )


@activity.defn
async def draft_reply(input: DraftReplyInput) -> str:
    context = (
        f"Ticket: {input.ticket.subject}\n{input.ticket.body}\n\n"
        f"Category: {input.classification.category}, "
        f"priority: {input.classification.priority}\n"
        f"Account: {input.account.account_name} ({input.account.plan} plan)"
    )
    response = await _openai_client().chat.completions.create(
        model=os.environ.get("MODEL_DRAFT", "gpt-4o-mini"),
        messages=[
            {"role": "system", "content": DRAFT_PROMPT},
            {"role": "user", "content": context},
        ],
        timeout=30,
    )
    return response.choices[0].message.content or ""
