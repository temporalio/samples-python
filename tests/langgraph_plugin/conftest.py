"""Shared test fixtures for LangGraph samples."""

import os

# Disable LangSmith tracing for tests to avoid rate limit issues
os.environ["LANGCHAIN_TRACING_V2"] = "false"

import pytest
from temporalio.contrib.langgraph._graph_registry import get_global_registry


@pytest.fixture(autouse=True)
def clear_registry() -> None:
    """Clear the global graph registry before each test."""
    get_global_registry().clear()


def has_openai_api_key() -> bool:
    """Check if OpenAI API key is available."""
    return bool(os.environ.get("OPENAI_API_KEY"))


# Skip marker for tests that require OpenAI API
requires_openai = pytest.mark.skipif(
    not has_openai_api_key(),
    reason="OPENAI_API_KEY environment variable not set",
)
