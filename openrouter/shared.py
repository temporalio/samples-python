from dataclasses import dataclass, field
from datetime import timedelta
from typing import Optional

from temporalio.common import RetryPolicy

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# OpenRouter's Auto Router picks a concrete model per request. The response's
# `model` field reports which one it chose.
DEFAULT_MODEL = "openrouter/auto"

PROMPT_BATCH_TASK_QUEUE = "openrouter-prompt-batch"
BUDGET_GATE_TASK_QUEUE = "openrouter-budget-gate"

# Each Activity adds a few events to the Workflow's Event History and each
# answer is stored in the Workflow result payload. Keep batches small enough to
# stay well under the history and payload limits; see the README for the
# sliding-window pattern for larger batches.
MAX_PROMPTS_PER_BATCH = 100

# A parked batch can wait at most this long (30 days) for a raise_budget.
MAX_APPROVAL_TIMEOUT_SECONDS = 30 * 24 * 3600

# Temporal owns retries: 1s, 2s, 4s, ... capped at 60s, five attempts. The
# Activity marks 4xx errors non-retryable and passes OpenRouter's Retry-After
# through as the next retry delay, so this policy only governs the rest.
OPENROUTER_RETRY_POLICY = RetryPolicy(
    initial_interval=timedelta(seconds=1),
    backoff_coefficient=2.0,
    maximum_interval=timedelta(seconds=60),
    maximum_attempts=5,
)


@dataclass
class OpenRouterRequest:
    """One chat completion request. Everything here ends up in the request
    body, so keep it free of per-attempt values (attempt number, timestamps):
    OpenRouter's response cache keys on the exact body, and a retried attempt
    should be byte-identical to the first one."""

    prompt: str
    model: str = DEFAULT_MODEL
    # When set, sent as OpenRouter's `models` list and tried in order. This
    # replaces the Auto Router.
    fallback_models: list[str] = field(default_factory=list)
    # Auto Router cost tier: low, medium, high, xhigh, or max. Only used with
    # `openrouter/auto`.
    cost_tier: str = "low"
    # How long OpenRouter keeps a successful response cached so that a retry of
    # the identical request is served for free.
    cache_ttl_seconds: int = 600
    # Demo hook: fail the first attempt *after* the response arrives, so the
    # retry shows a cache hit billed at $0 in Event History.
    fail_once_after_call: bool = False


@dataclass
class OpenRouterResult:
    prompt: str
    model: str
    answer: str
    # What OpenRouter reported for this attempt's response. None if the
    # response carried no usage.cost (it always should).
    cost_usd: Optional[float]
    generation_id: str
    # "HIT" or "MISS" from OpenRouter's X-OpenRouter-Cache-Status header, or ""
    # when the header is absent.
    cache_status: str


@dataclass
class SkippedPrompt:
    prompt: str
    reason: str


@dataclass
class BatchInput:
    prompts: list[str]
    model: str = DEFAULT_MODEL
    max_concurrency: int = 5
    fail_once_after_call: bool = False


@dataclass
class BatchResult:
    results: list[OpenRouterResult]
    skipped: list[SkippedPrompt]
    # Sum of the cost OpenRouter reported on each prompt's final, successful
    # attempt (budget_gate charges its estimate for a response with no cost).
    # Attempts that were billed but whose result never reached Temporal (a
    # Worker crash after the response, say) are not in here; OpenRouter's
    # dashboard or /api/v1/key is the source of truth for spend.
    reported_cost_usd: float


@dataclass
class BudgetGateInput:
    # The batch to run: prompts, model, concurrency. Same shape as prompt_batch.
    batch: BatchInput
    # Soft budget enforced by the Workflow from OpenRouter's reported cost.
    budget_usd: float
    # Reserved per in-flight call before its real cost is known. Reservations
    # count against the budget, so overshoot is bounded by
    # batch.max_concurrency * max(actual cost - estimate, 0): nothing if the
    # estimate is high enough, unbounded if it is far too low.
    estimated_cost_usd: float = 0.001
    # How long, from the start of the batch, parked prompts wait for a
    # `raise_budget` Update before the batch gives up on them. One deadline is
    # shared by the whole batch.
    approval_timeout_seconds: int = 3600


@dataclass
class LedgerEntry:
    prompt: str
    model: str
    # Reported cost, or the batch's estimate when the response had no cost.
    cost_usd: float
    cost_known: bool
    generation_id: str
    cache_status: str


@dataclass
class SpendReport:
    budget_usd: float
    spent_usd: float
    reserved_usd: float
    completed: int
    # Prompts currently parked, keyed by prompt text (duplicate prompts share
    # one entry), with why: "soft_budget_exhausted" or "insufficient_credits"
    # (OpenRouter refused the call for lack of credits).
    paused: dict[str, str]
    ledger: list[LedgerEntry]
