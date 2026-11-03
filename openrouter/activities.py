import asyncio
import json
import os
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Mapping, NoReturn, Optional

from openai import APIStatusError, AsyncOpenAI
from temporalio import activity
from temporalio.exceptions import ApplicationError

from openrouter.shared import (
    OPENROUTER_BASE_URL,
    OpenRouterRequest,
    OpenRouterResult,
)


def build_client(api_key: Optional[str] = None) -> AsyncOpenAI:
    """OpenAI SDK client pointed at OpenRouter.

    Client-side retries are disabled so that Temporal owns every retry: the
    attempt count and last failure land in Event History, and each attempt is
    logged below. (OpenRouter's official SDKs retry 5xx
    and connection errors for up to an hour by default; if you use one of them
    instead, turn that off too.)
    """
    default_headers: dict[str, str] = {}
    # App attribution is optional. When set, OpenRouter lists your app in its
    # public rankings; send X-OpenRouter-App-Visibility: hidden on the first
    # request to create the app entry as hidden.
    if referer := os.getenv("OPENROUTER_HTTP_REFERER"):
        default_headers["HTTP-Referer"] = referer
    if title := os.getenv("OPENROUTER_APP_TITLE"):
        default_headers["X-OpenRouter-Title"] = title
    return AsyncOpenAI(
        base_url=OPENROUTER_BASE_URL,
        api_key=api_key or os.environ["OPENROUTER_API_KEY"],
        max_retries=0,
        timeout=60.0,
        default_headers=default_headers or None,
    )


def error_type(status: int) -> str:
    """Error type recorded in Event History for an OpenRouter HTTP status."""
    return f"OpenRouterHTTP{status}"


# Raised instead of an HTTP status type when the call failed for lack of money:
# a 402 (OpenRouter documents this for both the account and the API key, with
# error.metadata.limit_source saying which) or, as observed in practice, a 403
# "Key limit exceeded" for a per-key limit. A Workflow can pause on this and
# resume once someone tops up.
OUT_OF_CREDITS = "OpenRouterOutOfCredits"

# A 402 from OpenRouter's in-flight budget cap is transient: wait for
# Retry-After and try again.
TRANSIENT_402_LIMIT_SOURCE = "openrouter_in_flight_budget"

# Longest Retry-After the Activity will pass through as the next retry delay.
MAX_RETRY_AFTER = timedelta(minutes=5)


def _retry_after(headers: Mapping[str, str]) -> Optional[timedelta]:
    """Parse Retry-After in either its delta-seconds or HTTP-date form."""
    value = (headers.get("retry-after") or "").strip()
    if not value:
        return None
    delay: Optional[timedelta] = None
    try:
        delay = timedelta(seconds=float(value))
    except (ValueError, OverflowError):
        try:
            delay = parsedate_to_datetime(value) - datetime.now(timezone.utc)
        except (TypeError, ValueError, OverflowError):
            return None
    if delay <= timedelta(0):
        return None
    # Honor the server, within reason: next_retry_delay overrides the retry
    # policy's interval, so cap it rather than park a prompt for hours.
    return min(delay, MAX_RETRY_AFTER)


def raise_for_status(
    status: int, error: Mapping[str, Any], headers: Mapping[str, str]
) -> NoReturn:
    """Turn an OpenRouter error into an ApplicationError with the right retry posture.

    `error` is OpenRouter's error object ({"code", "message", "metadata"}).
    Retryable: 408 (timeout), 429 (rate limited, honoring Retry-After), any
    5xx (500, 502 model down, 503 no provider available, 524, 529), and the
    transient in-flight-budget 402. Non-retryable: other 4xx. 400 is a bad
    request, 401 a bad key, 403 a moderation or permission block. Retrying
    those only costs time. Out of money is its own type (OUT_OF_CREDITS).
    """
    message = str(error.get("message") or "")
    metadata = error.get("metadata")
    limit_source = metadata.get("limit_source") if isinstance(metadata, dict) else None
    transient_402 = status == 402 and limit_source == TRANSIENT_402_LIMIT_SOURCE
    if not transient_402 and (
        status == 402 or (status == 403 and "limit exceeded" in message.lower())
    ):
        raise ApplicationError(
            f"OpenRouter returned HTTP {status}: {message}",
            {"status": status},
            type=OUT_OF_CREDITS,
            non_retryable=True,
        )
    retryable = transient_402 or status in (408, 429) or status >= 500
    raise ApplicationError(
        f"OpenRouter returned HTTP {status}: {message}",
        {"status": status},
        type=error_type(status),
        non_retryable=not retryable,
        next_retry_delay=_retry_after(headers) if retryable else None,
    )


def _error_object(body: Any) -> dict[str, Any]:
    """OpenRouter's error object from either a raw body or openai's APIError.body.

    A raw response body wraps it as {"error": {...}}; openai's APIError.body is
    already the inner object. Accept both.
    """
    if not isinstance(body, dict):
        return {}
    inner = body.get("error", body)
    return inner if isinstance(inner, dict) else {}


def _error_code(error: Mapping[str, Any], default: int) -> int:
    code = error.get("code")
    return code if isinstance(code, int) else default


def _content_to_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(
            part["text"]
            for part in content
            if isinstance(part, dict) and isinstance(part.get("text"), str)
        )
    return ""


async def _heartbeat_forever(interval: timedelta) -> None:
    while True:
        await asyncio.sleep(interval.total_seconds())
        activity.heartbeat(activity.info().attempt)


class OpenRouterActivities:
    def __init__(self, client: AsyncOpenAI) -> None:
        self._client = client

    # @@@SNIPSTART python-openrouter-call-activity
    @activity.defn
    async def call_openrouter(self, request: OpenRouterRequest) -> OpenRouterResult:
        """One chat completion. One HTTP call per attempt; Temporal retries."""
        # Heartbeat so a killed Worker is noticed after heartbeat_timeout
        # rather than after the full start_to_close_timeout.
        heartbeat_timeout = activity.info().heartbeat_timeout
        heartbeat_task = (
            asyncio.create_task(_heartbeat_forever(heartbeat_timeout / 2))
            if heartbeat_timeout
            else None
        )
        try:
            return await self._send(request)
        finally:
            if heartbeat_task:
                heartbeat_task.cancel()

    async def _send(self, request: OpenRouterRequest) -> OpenRouterResult:
        extra_body: dict[str, Any] = {}
        if request.fallback_models:
            # OpenRouter tries these in order within the same request.
            extra_body["models"] = request.fallback_models
        elif request.model == "openrouter/auto":
            extra_body["plugins"] = [
                {"id": "auto-router", "cost_tier": request.cost_tier}
            ]
        model = request.fallback_models[0] if request.fallback_models else request.model

        try:
            raw = await self._client.chat.completions.with_raw_response.create(
                model=model,
                messages=[{"role": "user", "content": request.prompt}],
                extra_body=extra_body or None,
                extra_headers={
                    # Ask OpenRouter to cache the successful response. A retry
                    # of the byte-identical request within the TTL is served
                    # from cache and billed at $0.
                    "X-OpenRouter-Cache": "true",
                    "X-OpenRouter-Cache-TTL": str(request.cache_ttl_seconds),
                },
            )
        except APIStatusError as e:
            error = _error_object(e.body)
            error.setdefault("message", e.message)
            raise_for_status(e.status_code, error, e.response.headers)
        # Connection errors and timeouts propagate as-is: Temporal retries them.

        payload = json.loads(raw.text)
        if isinstance(payload.get("error"), dict):
            # OpenRouter can return HTTP 200 with an error body and no choices
            # when the upstream provider failed after the request was accepted.
            error = _error_object(payload)
            raise_for_status(_error_code(error, 500), error, raw.headers)
        choices = payload.get("choices") or []
        choice_error = choices[0].get("error") if choices else None
        if isinstance(choice_error, dict):
            # Or a 200 with a partial answer and the provider's error on the
            # choice itself; a partial answer is not an answer.
            raise_for_status(_error_code(choice_error, 500), choice_error, raw.headers)
        if not choices:
            # No error and no answer: treat like a server error and retry.
            raise_for_status(500, {"message": "Response has no choices"}, raw.headers)

        usage = payload.get("usage") or {}
        cost = usage.get("cost")
        if not isinstance(cost, (int, float)):
            # OpenRouter reports cost on every response; if it is ever missing,
            # say so rather than pretending the call was free.
            activity.logger.warning("OpenRouter response has no usage.cost")
        result = OpenRouterResult(
            prompt=request.prompt,
            model=str(payload.get("model", model)),
            answer=_content_to_text((choices[0].get("message") or {}).get("content"))
            if choices
            else "",
            cost_usd=float(cost) if isinstance(cost, (int, float)) else None,
            generation_id=str(payload.get("id", "")),
            cache_status=raw.headers.get("x-openrouter-cache-status", ""),
        )
        activity.logger.info(
            "OpenRouter call completed: attempt=%d model=%s cost_usd=%s cache=%s id=%s",
            activity.info().attempt,
            result.model,
            "unknown" if result.cost_usd is None else f"{result.cost_usd:.6f}",
            result.cache_status or "-",
            result.generation_id,
        )

        if request.fail_once_after_call and activity.info().attempt == 1:
            # Demo hook: the Worker "crashes" after the response arrived. The
            # retry re-sends the identical request and gets a cache hit.
            raise ApplicationError(
                "Simulated failure after the response was received",
                type="SimulatedFailure",
            )

        return result

    # @@@SNIPEND
