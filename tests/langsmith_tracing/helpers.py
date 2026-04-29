"""Shared test helpers for LangSmith tracing tests."""

from langsmith_tracing.chatbot.activities import ChatResponse


def make_text_response(text: str) -> ChatResponse:
    """Build a minimal ChatResponse with a text output."""
    return ChatResponse(id="resp_mock", output_text=text)
