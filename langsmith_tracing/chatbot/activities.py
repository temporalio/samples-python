"""Chatbot activities with LangSmith tracing."""

from dataclasses import dataclass
from typing import Any

from langsmith import traceable
from langsmith.wrappers import wrap_openai
from openai import AsyncOpenAI
from pydantic import BaseModel, Field
from temporalio import activity


class ToolCall(BaseModel):
    call_id: str
    name: str
    arguments: str


class ChatResponse(BaseModel):
    id: str
    output_text: str = ""
    tool_calls: list[ToolCall] = Field(default_factory=list)


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
async def call_openai(request: OpenAIRequest) -> ChatResponse:
    """Call OpenAI Responses API. Retries handled by Temporal, not the OpenAI client."""
    # wrap_openai patches the client so each API call (e.g. responses.create)
    # creates its own child span with model parameters and token usage.
    # max_retries=0 disables OpenAI's built-in retries — Temporal's activity
    # retry policy handles retries instead, with full visibility in the UI.
    client = wrap_openai(AsyncOpenAI(max_retries=0))
    response_args: dict[str, Any] = {
        "model": request.model,
        "instructions": request.instructions,
        "input": request.input,
        "timeout": 30,
    }
    if request.tools:
        response_args["tools"] = request.tools
    if request.previous_response_id:
        response_args["previous_response_id"] = request.previous_response_id
    response = await client.responses.create(**response_args)
    return ChatResponse(
        id=response.id,
        output_text=response.output_text or "",
        tool_calls=[
            ToolCall(call_id=item.call_id, name=item.name, arguments=item.arguments)
            for item in response.output
            if item.type == "function_call"
        ],
    )
