from typing import Any

import pytest
from litellm import ModelResponse

from litellm_activity import activities
from litellm_activity.shared import LLMRequest


async def test_call_litellm(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    async def mock_acompletion(**kwargs: Any) -> ModelResponse:
        captured.update(kwargs)
        return ModelResponse(
            model="test-model",
            choices=[
                {
                    "index": 0,
                    "finish_reason": "stop",
                    "message": {"role": "assistant", "content": "Hello from LiteLLM"},
                }
            ],
        )

    monkeypatch.setattr(activities, "acompletion", mock_acompletion)

    result = await activities.call_litellm(
        LLMRequest(
            prompt="Hello",
            model="test/model",
            system_prompt="Be concise.",
        )
    )

    assert result == "Hello from LiteLLM"
    assert captured == {
        "model": "test/model",
        "messages": [
            {"role": "system", "content": "Be concise."},
            {"role": "user", "content": "Hello"},
        ],
        "timeout": 30,
        "num_retries": 0,
    }
