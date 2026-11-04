import asyncio
import os
import signal
import sys

import pytest
from temporalio.client import Client

pytestmark = pytest.mark.skipif(
    os.getenv("TEMPORAL_TEST_ACTIVITY_SESSION_SAMPLE") != "1",
    reason="requires the session SDK and a session-capable server",
)


@pytest.mark.parametrize(
    "entrypoint",
    [
        ["activity_sessions.affinity", "--modes", "none", "affinity", "single-session"],
        ["activity_sessions.single_session", "--turn-seconds", "0.2"],
    ],
    ids=["affinity", "single-session"],
)
async def test_entrypoint(
    client: Client, request: pytest.FixtureRequest, entrypoint: list[str]
) -> None:
    if request.config.getoption("--workflow-environment") in ("local", "time-skipping"):
        pytest.fail("Use --workflow-environment host:port for the custom server")
    demo = await asyncio.create_subprocess_exec(
        sys.executable,
        "-m",
        *entrypoint,
        "--steps",
        "4",
        "--fetch-seconds",
        "0.1",
        "--no-live",
        env={
            **os.environ,
            "TEMPORAL_ADDRESS": client.service_client.config.target_host,
            "TEMPORAL_NAMESPACE": client.namespace,
        },
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    try:
        output, _ = await asyncio.wait_for(demo.communicate(), 180)
        assert demo.returncode == 0, output.decode()
        assert "✗" not in output.decode()
    finally:
        if demo.returncode is None:
            demo.send_signal(signal.SIGINT)
            await asyncio.wait_for(demo.wait(), 25)
