import dataclasses
import json
from datetime import timedelta
from typing import Any, Callable

import httpx
import pytest
from openai import AsyncOpenAI
from temporalio.exceptions import ApplicationError
from temporalio.testing import ActivityEnvironment

from openrouter.activities import OpenRouterActivities
from openrouter.shared import OPENROUTER_BASE_URL, OpenRouterRequest

Handler = Callable[[httpx.Request], httpx.Response]


def make_activities(handler: Handler) -> OpenRouterActivities:
    """Activities backed by a fake OpenRouter; no network, no API key."""
    client = AsyncOpenAI(
        base_url=OPENROUTER_BASE_URL,
        api_key="test-key",
        max_retries=0,
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )
    return OpenRouterActivities(client)


def completion_body(
    answer: str = "Retries repeat a failed call.",
    model: str = "openai/gpt-4o-mini",
    cost: Any = 0.000123,
) -> dict[str, Any]:
    return {
        "id": "gen-123",
        "object": "chat.completion",
        "created": 0,
        "model": model,
        "choices": [
            {
                "index": 0,
                "finish_reason": "stop",
                "message": {"role": "assistant", "content": answer},
            }
        ],
        "usage": {
            "prompt_tokens": 5,
            "completion_tokens": 7,
            "total_tokens": 12,
            "cost": cost,
        },
    }


async def test_success_returns_model_cost_and_cache_status() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json=completion_body(),
            headers={"X-OpenRouter-Cache-Status": "MISS"},
        )

    result = await ActivityEnvironment().run(
        make_activities(handler).call_openrouter,
        OpenRouterRequest(prompt="Explain retries in one sentence."),
    )

    assert result.model == "openai/gpt-4o-mini"
    assert result.answer == "Retries repeat a failed call."
    assert result.cost_usd == pytest.approx(0.000123)
    assert result.generation_id == "gen-123"
    assert result.cache_status == "MISS"

    # Exactly one HTTP call per attempt: the client does not retry on its own.
    assert len(requests) == 1
    body = json.loads(requests[0].content)
    assert body["model"] == "openrouter/auto"
    assert body["plugins"] == [{"id": "auto-router", "cost_tier": "low"}]
    assert requests[0].headers["X-OpenRouter-Cache"] == "true"
    assert requests[0].headers["X-OpenRouter-Cache-TTL"] == "600"


async def test_fallback_models_replace_auto_router() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json=completion_body(model="b/second"))

    result = await ActivityEnvironment().run(
        make_activities(handler).call_openrouter,
        OpenRouterRequest(prompt="hi", fallback_models=["a/first", "b/second"]),
    )

    body = json.loads(requests[0].content)
    assert body["model"] == "a/first"
    assert body["models"] == ["a/first", "b/second"]
    assert "plugins" not in body
    assert result.model == "b/second"


async def test_rate_limit_is_retryable_and_honors_retry_after() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            429,
            json={"error": {"code": 429, "message": "Rate limited"}},
            headers={"Retry-After": "7"},
        )

    with pytest.raises(ApplicationError) as excinfo:
        await ActivityEnvironment().run(
            make_activities(handler).call_openrouter, OpenRouterRequest(prompt="hi")
        )

    assert excinfo.value.type == "OpenRouterHTTP429"
    assert not excinfo.value.non_retryable
    assert excinfo.value.next_retry_delay == timedelta(seconds=7)


async def test_insufficient_credits_is_non_retryable() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            402, json={"error": {"code": 402, "message": "Insufficient credits"}}
        )

    with pytest.raises(ApplicationError) as excinfo:
        await ActivityEnvironment().run(
            make_activities(handler).call_openrouter, OpenRouterRequest(prompt="hi")
        )

    assert excinfo.value.type == "OpenRouterHTTP402"
    assert excinfo.value.non_retryable
    assert "Insufficient credits" in str(excinfo.value)


async def test_server_error_is_retryable() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(502, json={"error": {"code": 502, "message": "down"}})

    with pytest.raises(ApplicationError) as excinfo:
        await ActivityEnvironment().run(
            make_activities(handler).call_openrouter, OpenRouterRequest(prompt="hi")
        )

    assert excinfo.value.type == "OpenRouterHTTP502"
    assert not excinfo.value.non_retryable


async def test_error_body_inside_200_is_classified_by_its_code() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"error": {"code": 403, "message": "Flagged by moderation"}},
        )

    with pytest.raises(ApplicationError) as excinfo:
        await ActivityEnvironment().run(
            make_activities(handler).call_openrouter, OpenRouterRequest(prompt="hi")
        )

    assert excinfo.value.type == "OpenRouterHTTP403"
    assert excinfo.value.non_retryable


async def test_fail_once_after_call_fails_first_attempt_only() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json=completion_body(cost=0),
            headers={"X-OpenRouter-Cache-Status": "HIT"},
        )

    activities = make_activities(handler)
    request = OpenRouterRequest(prompt="hi", fail_once_after_call=True)

    env = ActivityEnvironment()
    with pytest.raises(ApplicationError) as excinfo:
        await env.run(activities.call_openrouter, request)
    assert excinfo.value.type == "SimulatedFailure"
    assert not excinfo.value.non_retryable

    env.info = dataclasses.replace(env.info, attempt=2)
    result = await env.run(activities.call_openrouter, request)
    assert result.cache_status == "HIT"
    assert result.cost_usd == 0.0


async def test_missing_cost_is_reported_as_zero() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        body = completion_body()
        del body["usage"]["cost"]
        return httpx.Response(200, json=body)

    result = await ActivityEnvironment().run(
        make_activities(handler).call_openrouter, OpenRouterRequest(prompt="hi")
    )
    assert result.cost_usd == 0.0
    assert result.cache_status == ""
