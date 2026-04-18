"""Chatbot activities with LangSmith tracing."""

from dataclasses import dataclass

from langsmith import traceable
from langsmith.wrappers import wrap_openai
from openai import AsyncOpenAI
from openai.types.responses import Response
from temporalio import activity


@dataclass
class OpenAIRequest:
    model: str
    input: str | list
    instructions: str = (
        "You are a helpful assistant with note-taking abilities. "
        "Use save_note to remember things and read_note to recall them."
    )
    tools: list | None = None
    previous_response_id: str | None = None


# wrap_openai automatically traces LLM calls in LangSmith — capturing
# model parameters, token usage, and latency without extra code.
@traceable(name="Call OpenAI", run_type="llm")
@activity.defn
async def call_openai(request: OpenAIRequest) -> Response:
    """Call OpenAI Responses API. Retries handled by Temporal."""
    client = wrap_openai(AsyncOpenAI(max_retries=0))
    kwargs: dict = {
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


# run_type="tool" tells LangSmith this is a tool execution, which renders
# distinctly in the trace UI alongside LLM calls and chains.
@traceable(name="Save Note", run_type="tool")
@activity.defn
async def save_note(name: str, content: str) -> str:
    """Save a note. Durable side effect — survives worker crashes."""
    activity.logger.info(f"Saving note '{name}': {content[:80]}")
    return f"Saved note '{name}'."
