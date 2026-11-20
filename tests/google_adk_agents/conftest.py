"""Skip the Google ADK sample tests on Python 3.10.

On the CI runners' Python 3.10, these Workflows trip the SDK's two-second
deadlock detector; the evicted run never finishes and the job hangs until its
timeout. CI still runs them on Python 3.14, and Temporal Python SDK 1.36 drops
Python 3.10.
"""

import sys

import pytest


@pytest.fixture(autouse=True)
def _skip_on_python_310() -> None:
    if sys.version_info < (3, 11):
        pytest.skip(
            "Google ADK sample Workflows can hang CI on Python 3.10; run on 3.11+"
        )
