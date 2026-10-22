import asyncio
import os
import signal
import sys

import pytest
from temporalio.client import Client

pytestmark = pytest.mark.skipif(
    os.getenv("TEMPORAL_TEST_ACTIVITY_SESSION_SAMPLE") != "1",
    reason="requires the session SDK and custom server from temporal#12630",
)


@pytest.mark.parametrize(
    "session_workers,activity_workers",
    [(2, 1), (10, 0), (1, 9)],
    ids=["three-workers", "ten-session-workers", "one-session-nine-activity-workers"],
)
async def test_demo_cli(
    client: Client,
    request: pytest.FixtureRequest,
    session_workers: int,
    activity_workers: int,
) -> None:
    if request.config.getoption("--workflow-environment") in ("local", "time-skipping"):
        pytest.fail("Use --workflow-environment host:port for the custom server")
    demo = await asyncio.create_subprocess_exec(
        sys.executable,
        "-m",
        "activity_sessions.run",
        "--session-workers",
        str(session_workers),
        "--activity-workers",
        str(activity_workers),
        "--workflows",
        "2",
        "--steps",
        "3",
        "--load-seconds",
        "0.2",
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
        output, _ = await asyncio.wait_for(demo.communicate(), 120)
        assert demo.returncode == 0, output.decode()
        assert "Verified: each of 2 workflow(s)" in output.decode()
        print(output.decode())
    finally:
        if demo.returncode is None:
            demo.send_signal(signal.SIGINT)
            await asyncio.wait_for(demo.wait(), 25)
