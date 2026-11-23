"""Collection guard and Redis server for the tests of the Streams sample on Redis.

The Streams API of `temporalio` and the `temporalio-streams-redis` package have no
release yet, so the environment of this repo has neither. The test module imports
both, and `collect_ignore_glob` skips it before that import fails, as
`tests/microsoft_agent_framework_plugin/conftest.py` does for its plugin.
"""

import shutil
import socket
import subprocess
import tempfile
import time
from collections.abc import Iterator

import pytest

collect_ignore_glob: list[str] = []

try:
    import temporalio_streams_redis  # noqa: F401
    from temporalio.client import StreamConfig  # noqa: F401
except ImportError:
    collect_ignore_glob = ["*_test.py"]


def pytest_report_header(config) -> str | None:
    if collect_ignore_glob:
        return (
            "streams_redis: the Streams API or temporalio-streams-redis isn't "
            "installed, so its tests are NOT collected "
            "(see tests/streams_redis/conftest.py)"
        )
    return None


@pytest.fixture(scope="session")
def redis_url() -> Iterator[str]:
    """Start a `redis-server` on a free port."""
    binary = shutil.which("redis-server")
    if binary is None:
        pytest.skip("redis-server isn't on the PATH")
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    directory = tempfile.mkdtemp(prefix="streams-redis-")
    process = subprocess.Popen(
        [binary, "--bind", "127.0.0.1", "--port", str(port)]
        + ["--save", "", "--appendonly", "no", "--dir", directory],
        stdout=subprocess.DEVNULL,
    )
    try:
        deadline = time.monotonic() + 20
        while True:
            try:
                socket.create_connection(("127.0.0.1", port), timeout=1).close()
                break
            except OSError:
                assert process.poll() is None, "redis-server didn't start"
                assert time.monotonic() < deadline, "redis-server didn't start"
                time.sleep(0.05)
        yield f"redis://127.0.0.1:{port}"
    finally:
        process.kill()
        process.wait()
        shutil.rmtree(directory, ignore_errors=True)
