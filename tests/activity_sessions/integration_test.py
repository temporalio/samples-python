import asyncio
import os
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
    "activity_worker_count", [1, 8], ids=["three-workers", "ten-workers"]
)
async def test_comparison_with_independent_worker_processes(
    client: Client,
    request: pytest.FixtureRequest,
    tmp_path: Path,
    activity_worker_count: int,
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
    processes = []
    logs = []
    worker_specs = [
        ("worker-1", False),
        ("worker-2", False),
        *[(f"worker-{index + 3}", True) for index in range(activity_worker_count)],
    ]
    try:
        for identity, activity_only in worker_specs:
            log = (tmp_path / f"{identity}.log").open("w")
            logs.append(log)
            args = [
                sys.executable,
                "-m",
                "activity_sessions.worker",
                "--identity",
                identity,
                "--task-queue",
                task_queue,
                "--context-file",
                str(context_file),
            ]
            if activity_only:
                args.append("--activity-only")
            processes.append(
                await asyncio.create_subprocess_exec(
                    *args, env=environment, stdout=log, stderr=asyncio.subprocess.STDOUT
                )
            )

        async def workers_are_polling() -> None:
            for process in processes:
                assert process.returncode is None, "\n".join(
                    path.read_text() for path in tmp_path.glob("*.log")
                )
            for kind, expected in [
                (TaskQueueType.TASK_QUEUE_TYPE_WORKFLOW, {"worker-1", "worker-2"}),
                (
                    TaskQueueType.TASK_QUEUE_TYPE_ACTIVITY,
                    {identity for identity, _ in worker_specs},
                ),
            ]:
                description = await client.workflow_service.describe_task_queue(
                    DescribeTaskQueueRequest(
                        namespace=client.namespace,
                        task_queue=TaskQueue(name=task_queue),
                        # Readiness must include pollers on every normal-queue partition.
                        api_mode=DescribeTaskQueueMode.DESCRIBE_TASK_QUEUE_MODE_ENHANCED,
                        task_queue_types=[kind],
                        versions=TaskQueueVersionSelection(unversioned=True),
                        report_pollers=True,
                    )
                )
                assert expected <= {
                    poller.identity
                    for version in description.versions_info.values()
                    for poller in version.types_info[kind].pollers
                }

        await assert_eventually(workers_are_polling)
        starter = await asyncio.create_subprocess_exec(
            sys.executable,
            "-m",
            "activity_sessions.starter",
            "--task-queue",
            task_queue,
            "--session-workers",
            "worker-1",
            "worker-2",
            "--activity-workers",
            *[identity for identity, activity_only in worker_specs if activity_only],
            env=environment,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        processes.append(starter)
        output, _ = await asyncio.wait_for(starter.communicate(), 60)
        assert starter.returncode == 0, output.decode()
        print(output.decode())
    finally:
        for process in processes:
            if process.returncode is None:
                process.terminate()
        for process in processes:
            try:
                await asyncio.wait_for(process.wait(), 15)
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
        for log in logs:
            log.close()
    assert all(process.returncode == 0 for process in processes)
