"""Activity for LLM interactions using litellm."""

import json
from dataclasses import dataclass
from typing import Any, Dict, Optional, cast

import litellm
from litellm.types.utils import Choices, ModelResponse
from temporalio import activity


@dataclass
class LLMRequest:
    """Request for LLM completion."""

    system_prompt: str
    user_prompt: str
    model: str = "claude-3-5-sonnet-20241022"
    temperature: float = 0.7
    max_tokens: int = 1000


@dataclass
class LLMResponse:
    """Response from LLM completion."""

    content: str
    model: str
    usage: Optional[Dict[str, Any]] = None


@activity.defn
async def call_llm(request: LLMRequest) -> LLMResponse:
    """Call an LLM using litellm."""

    litellm.suppress_debug_info = True

    messages = [
        {"role": "system", "content": request.system_prompt},
        {"role": "user", "content": request.user_prompt},
    ]

    response = cast(
        ModelResponse,
        await litellm.acompletion(
            model=request.model,
            messages=messages,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        ),
    )
    choices = cast(list[Choices], response.choices)
    content = choices[0].message.content
    assert content
    assert response.model

    return LLMResponse(content=content, model=response.model)


@activity.defn
async def parse_json_response(response: str) -> Dict[str, Any]:
    """Parse JSON from LLM response, handling markdown code blocks."""
    # Remove markdown code blocks if present
    if "```json" in response:
        start = response.find("```json") + 7
        end = response.find("```", start)
        if end != -1:
            response = response[start:end].strip()
    elif "```" in response:
        start = response.find("```") + 3
        end = response.find("```", start)
        if end != -1:
            response = response[start:end].strip()

    # Try to parse the JSON
    try:
        return json.loads(response.strip())
    except json.JSONDecodeError as e:
        # If parsing fails, try to extract JSON object from the response
        # Look for the first { and last }
        start = response.find("{")
        end = response.rfind("}")
        if start != -1 and end != -1:
            try:
                return json.loads(response[start : end + 1])
            except json.JSONDecodeError:
                pass
        raise ValueError(f"Failed to parse JSON from response: {e}")
