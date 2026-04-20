"""Basic LLM activity with LangSmith tracing."""

from dataclasses import dataclass

from langsmith import traceable
from langsmith.wrappers import wrap_openai
from openai import AsyncOpenAI
from openai.types.responses import Response
from temporalio import activity


@dataclass
class OpenAIRequest:
    model: str
    input: str
    instructions: str = "You are a helpful assistant."


# @traceable creates a named span in LangSmith. wrap_openai further enriches
# the trace with model parameters, token counts, and latency automatically.
@traceable(name="Call OpenAI", run_type="llm")
@activity.defn
async def call_openai(request: OpenAIRequest) -> Response:
    """Call OpenAI Responses API. Retries handled by Temporal."""
    client = wrap_openai(AsyncOpenAI(max_retries=0))
    return await client.responses.create(
        model=request.model,
        instructions=request.instructions,
        input=request.input,
        timeout=30,
    )
