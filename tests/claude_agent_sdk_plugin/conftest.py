import sys
from pathlib import Path

import pytest
import pytest_asyncio
from temporalio.client import Client
from temporalio.testing import WorkflowEnvironment

collect_ignore_glob: list[str] = []

if sys.platform == "win32":
    collect_ignore_glob = ["*_test.py"]
else:
    try:
        import temporalio.claude_agent_sdk  # noqa: F401
    except ImportError:
        collect_ignore_glob = ["*_test.py"]


@pytest_asyncio.fixture
async def client(env: WorkflowEnvironment) -> Client:
    if env.supports_time_skipping:
        pytest.skip("Claude Code runs in real time")
    return env.client


@pytest.fixture(autouse=True)
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.chdir(tmp_path)
    return tmp_path
