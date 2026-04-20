"""Chatbot activities with LangSmith tracing."""

from dataclasses import dataclass
from typing import Any

from langsmith import traceable
from langsmith.wrappers import wrap_openai
from openai import AsyncOpenAI
from openai.types.responses import Response
from temporalio import activity


@dataclass
class OpenAIRequest:
    model: str
    # str for the initial user prompt, list for tool call results fed back
    input: str | list[dict[str, Any]]
    instructions: str = (
        "You are a helpful assistant with note-taking abilities. "
        "Use save_note to remember things and read_note to recall them."
    )
    tools: list[dict[str, Any]] | None = None
    previous_response_id: str | None = None


@traceable(name="Call OpenAI", run_type="llm")
@activity.defn
async def call_openai(request: OpenAIRequest) -> Response:
    """Call OpenAI Responses API. Retries handled by Temporal, not the OpenAI client."""
    # wrap_openai patches the client so each API call (e.g. responses.create)
    # creates its own child span with model parameters and token usage.
    client = wrap_openai(AsyncOpenAI(max_retries=0))
    kwargs: dict[str, Any] = {
        "model": request.model,
        "instructions": request.instructions,
        "input": request.input,
        "timeout": 30,
    }
    if request.tools:
        kwargs["tools"] = request.tools
    if request.previous_response_id:
        kwargs["previous_response_id"] = request.previous_response_id
    return await client.responses.create(**kwargs)
