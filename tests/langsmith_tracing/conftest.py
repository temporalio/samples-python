"""Shared fixtures for LangSmith tracing tests."""

from unittest.mock import MagicMock

import pytest


@pytest.fixture
def mock_ls_client() -> MagicMock:
    """Return a mock ``langsmith.Client`` that never makes network calls.

    The samples tests don't assert on trace output — the LangSmith plugin
    just needs *some* client object to wire into the worker.  ``MagicMock``
    auto-stubs every method the interceptor calls; the explicit ``session``
    and ``tracing_queue`` stubs match what the langsmith library touches
    internally.
    """
    client = MagicMock()
    client.session = MagicMock()
    client.tracing_queue = MagicMock()
    return client
