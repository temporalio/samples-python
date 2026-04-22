"""Shared test helpers for LangSmith tracing tests."""

from openai.types.responses import Response
from openai.types.responses.response_output_message import ResponseOutputMessage
from openai.types.responses.response_output_text import ResponseOutputText


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
