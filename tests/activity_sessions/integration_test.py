import asyncio
import os
import signal
import sys
import uuid
from pathlib import Path

import pytest
from temporalio.api.enums.v1 import DescribeTaskQueueMode, TaskQueueType
from temporalio.api.taskqueue.v1 import TaskQueue, TaskQueueVersionSelection
from temporalio.api.workflowservice.v1 import DescribeTaskQueueRequest
from temporalio.client import Client

from tests.helpers import assert_eventually

pytestmark = pytest.mark.skipif(
    os.getenv("TEMPORAL_TEST_ACTIVITY_SESSION_SAMPLE") != "1",
    reason="requires the session SDK and custom server from temporal#12630",
)


@pytest.mark.parametrize(
    "session_workers,activity_workers",
    [(2, 1), (10, 0), (1, 9)],
    ids=["three-workers", "ten-session-workers", "one-session-nine-activity-workers"],
)
async def test_pool_and_starter_cli(
    client: Client,
    request: pytest.FixtureRequest,
    tmp_path: Path,
    session_workers: int,
    activity_workers: int,
) -> None:
    if request.config.getoption("--workflow-environment") in ("local", "time-skipping"):
        pytest.fail("Use --workflow-environment host:port for the custom server")
    task_queue = f"session-cache-{uuid.uuid4()}"
    context_file = tmp_path / "conversation.txt"
    context_file.write_text("Conversation context")
    environment = {
        **os.environ,
        "TEMPORAL_ADDRESS": client.service_client.config.target_host,
        "TEMPORAL_NAMESPACE": client.namespace,
    }
    counts = [
        "--session-workers",
        str(session_workers),
        "--activity-workers",
        str(activity_workers),
    ]
    processes = []
    with (tmp_path / "pool.log").open("w") as log:
        try:
            pool = await asyncio.create_subprocess_exec(
                sys.executable,
                "-m",
                "activity_sessions.pool",
                *counts,
                "--task-queue",
                task_queue,
                "--context-file",
                str(context_file),
                env=environment,
                stdout=log,
                stderr=asyncio.subprocess.STDOUT,
            )
            processes.append(pool)

            async def workers_are_polling() -> None:
                assert pool.returncode is None, (tmp_path / "pool.log").read_text()
                for kind, count in [
                    (TaskQueueType.TASK_QUEUE_TYPE_WORKFLOW, session_workers),
                    (
                        TaskQueueType.TASK_QUEUE_TYPE_ACTIVITY,
                        session_workers + activity_workers,
                    ),
                ]:
                    description = await client.workflow_service.describe_task_queue(
                        DescribeTaskQueueRequest(
                            namespace=client.namespace,
                            task_queue=TaskQueue(name=task_queue),
                            api_mode=DescribeTaskQueueMode.DESCRIBE_TASK_QUEUE_MODE_ENHANCED,
                            task_queue_types=[kind],
                            versions=TaskQueueVersionSelection(unversioned=True),
                            report_pollers=True,
                        )
                    )
                    observed = {
                        poller.identity
                        for version in description.versions_info.values()
                        for poller in version.types_info[kind].pollers
                    }
                    assert {f"worker-{index + 1}" for index in range(count)} <= observed

            await assert_eventually(workers_are_polling)
            starter = await asyncio.create_subprocess_exec(
                sys.executable,
                "-m",
                "activity_sessions.starter",
                *counts,
                "--task-queue",
                task_queue,
                "--workflows",
                "2",
                env=environment,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            processes.append(starter)
            output, _ = await asyncio.wait_for(starter.communicate(), 60)
            assert starter.returncode == 0, output.decode()
            assert "Verified: 2 context load(s)" in output.decode()
            print(output.decode())
        finally:
            for process in processes:
                if process.returncode is None:
                    if sys.platform == "win32":
                        process.terminate()
                    else:
                        process.send_signal(signal.SIGINT)
            for process in processes:
                try:
                    await asyncio.wait_for(process.wait(), 20)
                except asyncio.TimeoutError:
                    process.kill()
                    await process.wait()
    if sys.platform != "win32":
        assert all(process.returncode == 0 for process in processes)
