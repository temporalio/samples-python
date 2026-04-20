"""Shared test helpers for LangSmith tracing tests."""

import asyncio
from typing import Any

from openai.types.responses import Response
from openai.types.responses.response_output_message import ResponseOutputMessage
from openai.types.responses.response_output_text import ResponseOutputText
from temporalio.client import WorkflowHandle


def make_text_response(text: str) -> Response:
    """Build a minimal OpenAI Response with a text output."""
    return Response.model_construct(
        id="resp_mock",
        created_at=0.0,
        model="gpt-4o-mini",
        object="response",
        output=[
            ResponseOutputMessage.model_construct(
                id="msg_mock",
                type="message",
                role="assistant",
                status="completed",
                content=[
                    ResponseOutputText.model_construct(
                        type="output_text",
                        text=text,
                        annotations=[],
                    )
                ],
            )
        ],
        parallel_tool_calls=False,
        tool_choice="auto",
        tools=[],
    )


async def poll_last_response(
    wf_handle: WorkflowHandle[Any, Any],
    query: Any,
    prev_response: str = "",
    timeout_seconds: float = 4.0,
    interval: float = 0.2,
) -> str:
    """Poll a workflow query until the response changes from prev_response."""
    iterations = int(timeout_seconds / interval)
    for _ in range(iterations):
        await asyncio.sleep(interval)
        response = await wf_handle.query(query)
        if response and response != prev_response:
            return response  # type: ignore[return-value]
    raise TimeoutError(
        f"Timed out after {timeout_seconds}s waiting for workflow response"
    )
