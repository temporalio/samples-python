"""Close every Gemini client the tests create.

``GeminiTestServer.plugin()`` builds a ``google.genai.Client`` per call and
nothing closes it afterwards. The client's finalizer then schedules
``aclose()`` on whatever event loop happens to be running when garbage
collection reaches the object, which can be a later test's loop or a
workflow's sandboxed loop. Closing the clients on this loop, while the test
that made them is still alive, keeps that from happening.
"""

from collections.abc import AsyncIterator
from typing import Any

import pytest
import pytest_asyncio
import temporalio.google_genai.testing as genai_testing
from google.genai import Client


@pytest_asyncio.fixture(autouse=True)
async def close_gemini_clients(monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[None]:
    created: list[Client] = []

    def tracking_client(*args: Any, **kwargs: Any) -> Client:
        client = Client(*args, **kwargs)
        created.append(client)
        return client

    monkeypatch.setattr(genai_testing, "GeminiClient", tracking_client)
    yield
    for client in created:
        await client.aio.aclose()
