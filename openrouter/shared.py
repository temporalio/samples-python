from dataclasses import dataclass, field
from typing import Optional

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
    cost_usd: float
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
    total_cost_usd: float


@dataclass
class BudgetGateInput:
    prompts: list[str]
    # Soft budget enforced by the Workflow from OpenRouter's reported cost.
    budget_usd: float
    # Reserved per in-flight call before its real cost is known. Overshoot is
    # bounded by max_concurrency * estimated_cost_usd.
    estimated_cost_usd: float = 0.001
    model: str = DEFAULT_MODEL
    max_concurrency: int = 3
    # How long a paused batch waits for a `raise_budget` Update before giving
    # up on the remaining prompts.
    approval_timeout_seconds: int = 3600


@dataclass
class LedgerEntry:
    prompt: str
    model: str
    cost_usd: float
    generation_id: str
    cache_status: str


@dataclass
class SpendReport:
    budget_usd: float
    spent_usd: float
    reserved_usd: float
    completed: int
    # Prompts currently parked, with why: "soft_budget_exhausted" or
    # "insufficient_credits" (OpenRouter returned 402).
    paused: dict[str, str]
    ledger: list[LedgerEntry]
    paused_reason: Optional[str] = None
