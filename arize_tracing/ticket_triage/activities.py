"""Activities for the ticket triage sample.

All LLM and I/O work happens here, never in workflow code. The worker
instruments the OpenAI client, so each API call below emits an OpenInference
LLM span (model, token usage, messages) nested under the activity's span.
"""

import asyncio
import json
import os
from dataclasses import dataclass
from typing import Awaitable, Optional, TypeVar

from openai import AsyncOpenAI
from temporalio import activity
from temporalio.exceptions import ApplicationError

# Demo hooks set from worker.py flags: module state in the worker process, not
# activity inputs, which would be recorded in workflow history.
# --fail-first-attempt: classify_ticket fails on attempt 1
FAIL_FIRST_ATTEMPT = False
# --slow-classify N: classify_ticket heartbeats N seconds before calling the LLM
SLOW_CLASSIFY_SECONDS = 0


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


_openai: Optional[AsyncOpenAI] = None


def _openai_client() -> AsyncOpenAI:
    """One OpenAI client per worker process, created on first use.

    Lazy so importing this module (the tests do, mocking the activities) needs
    no OPENAI_API_KEY. max_retries=0 leaves retries to Temporal's activity
    retry policy, which shows every attempt in the UI and in Arize.
    """
    global _openai
    if _openai is None:
        _openai = AsyncOpenAI(
            base_url=os.environ.get("OPENAI_BASE_URL"),
            api_key=os.environ.get("OPENAI_API_KEY"),
            max_retries=0,
        )
    return _openai


async def close_openai_client() -> None:
    """Close the shared client; the worker calls this on shutdown."""
    global _openai
    if _openai is not None:
        await _openai.close()
        _openai = None


def parse_classification(text: str) -> Classification:
    try:
        data = json.loads(text[text.index("{") : text.rindex("}") + 1])
        return Classification(
            category=str(data.get("category", "other")).lower(),
            priority=str(data.get("priority", "normal")).lower(),
        )
    except ValueError:
        return Classification(category="other", priority="normal")


# @@@SNIPSTART python-arize-tracing-activity
T = TypeVar("T")


async def _heartbeating(awaitable: Awaitable[T], every: float = 2.0) -> T:
    """Await ``awaitable`` while heartbeating every ``every`` seconds.

    ``classify_ticket`` runs with a 10-second heartbeat timeout so a worker
    that dies mid-attempt is noticed quickly; a slow LLM call must keep
    heartbeating or it would be retried while still in flight.
    """
    task = asyncio.ensure_future(awaitable)
    try:
        while True:
            done, _ = await asyncio.wait({task}, timeout=every)
            if done:
                return task.result()
            activity.heartbeat()
    except asyncio.CancelledError:
        task.cancel()
        raise


@activity.defn
async def classify_ticket(ticket: Ticket) -> Classification:
    if FAIL_FIRST_ATTEMPT and activity.info().attempt == 1:
        # Demo: a transient failure on the first attempt. Temporal retries the
        # activity; Arize shows one RunActivity span per attempt, the first
        # with an error status.
        raise ApplicationError(
            "Simulated transient LLM failure on attempt 1", type="SimulatedFailure"
        )
    if SLOW_CLASSIFY_SECONDS:
        # Demo: a slow attempt you can kill the worker during. The heartbeats
        # stop with the worker, so Temporal retries after the heartbeat timeout.
        await _heartbeating(asyncio.sleep(SLOW_CLASSIFY_SECONDS))
    response = await _heartbeating(
        _openai_client().chat.completions.create(
            model=os.environ.get("MODEL_CLASSIFY", "gpt-4o-mini"),
            messages=[
                {"role": "system", "content": CLASSIFY_PROMPT},
                {"role": "user", "content": f"{ticket.subject}\n\n{ticket.body}"},
            ],
            timeout=30,
        )
    )
    return parse_classification(response.choices[0].message.content or "")


# @@@SNIPEND


@activity.defn
async def lookup_account(customer_email: str) -> AccountInfo:
    """Look up the account name and plan for a customer email address."""
    # A plain (non-LLM) activity. The agents sample exposes it as a tool, and
    # the Agents SDK uses this docstring as the tool description.
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
