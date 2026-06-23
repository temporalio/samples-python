from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any

import pytest
from google.adk.models import BaseLlm, LLMRegistry
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.genai.types import Content, FunctionCall, Part

MODEL = "gemini-2.5-flash"


def text(s: str) -> LlmResponse:
    return LlmResponse(content=Content(role="model", parts=[Part(text=s)]))


def tool_call(name: str, args: dict[str, Any]) -> LlmResponse:
    return LlmResponse(
        content=Content(
            role="model",
            parts=[Part(function_call=FunctionCall(name=name, args=args))],
        )
    )


def patch_model(
    monkeypatch: pytest.MonkeyPatch,
    responses: list[LlmResponse],
    *,
    stream_chunks: bool = False,
) -> None:
    script = list(responses)
    orig_new_llm = LLMRegistry.new_llm  # staticmethod

    class _Mock(BaseLlm):
        async def generate_content_async(
            self, llm_request: LlmRequest, stream: bool = False
        ) -> AsyncGenerator[LlmResponse, None]:
            if stream_chunks:
                # The streaming sample is single-turn, so yield every scripted
                # chunk on this one call.
                while script:
                    yield script.pop(0)
                return
            if not script:
                raise AssertionError("mock model script exhausted")
            yield script.pop(0)

    def fake_new_llm(model: str) -> BaseLlm:
        if model == MODEL:
            return _Mock(model=model)
        return orig_new_llm(model)

    monkeypatch.setattr(LLMRegistry, "new_llm", staticmethod(fake_new_llm))
