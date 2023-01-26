import random
import uuid
from datetime import timedelta
from typing import Dict, List
from unittest import mock

import pytest
from temporalio import activity, exceptions
from temporalio.client import Client, WorkflowFailureError
from temporalio.common import RetryPolicy
from temporalio.worker import Worker

from activity_sticky_queues import tasks

CHECKSUM = "a checksum"
RETURNED_PATH = "valid/path"


def check_sticky_activity_count(history: List[Dict], nonsticky_queue: str):
    outputs = set()
    for item in history:
        if item.get("eventType", None) != "EVENT_TYPE_ACTIVITY_TASK_SCHEDULED":
            continue
        queue = item["activityTaskScheduledEventAttributes"]["taskQueue"]["name"]
        if queue != nonsticky_queue:
            outputs.add(queue)

    # handle lazy cases where all tasks assigned to the same worker
    return len(outputs) if len(outputs) > 1 else 1


@activity.defn(name="download_file_to_worker_filesystem")
async def mock_download(details: tasks.DownloadObj) -> str:
    return RETURNED_PATH


@activity.defn(name="work_on_file_in_worker_filesystem")
async def mock_work(path: str) -> str:
    return CHECKSUM


@activity.defn(name="work_on_file_in_worker_filesystem")
async def mock_work_fail(path: str) -> str:
    raise exceptions.ActivityError("testing graceful failure")


@activity.defn(name="clean_up_file_from_worker_filesystem")
async def mock_cleanup(path: str) -> None:
    pass


async def test_processing_fails_gracefully(client: Client):
    task_queue_name = str(uuid.uuid4())

    @activity.defn(name="get_available_task_queue")
    async def mock_task_queue():
        return task_queue_name

    async with Worker(
        client,
        task_queue=task_queue_name,
        workflows=[tasks.FileProcessing],
        activities=[
            mock_download,
            mock_work_fail,
            tasks.clean_up_file_from_worker_filesystem,
            mock_task_queue,
        ],
    ):
        exception_catch = pytest.raises(WorkflowFailureError)
        with exception_catch, mock.patch.object(tasks, "delete_file") as mock_del:
            await client.execute_workflow(
                tasks.FileProcessing.run,
                id=str(uuid.uuid4()),
                task_queue=task_queue_name,
                retry_policy=RetryPolicy(
                    maximum_attempts=1,
                    maximum_interval=timedelta(milliseconds=50),
                ),
                run_timeout=timedelta(milliseconds=50),
            )
        mock_del.assert_called_once()


async def test_worker_runs(client: Client):
    task_queue_name_distribution = str(uuid.uuid4())
    task_queue_workers = [str(uuid.uuid4()) for _ in range(3)]

    @activity.defn(name="get_available_task_queue")
    async def mock_task_queue():
        return random.choice(task_queue_workers)

    worker_distribution = Worker(
        client,
        task_queue=task_queue_name_distribution,
        workflows=[tasks.FileProcessing],
        activities=[
            mock_task_queue,
        ],
    )
    worker_1, worker_2, worker_3 = [
        Worker(
            client,
            task_queue=queue,
            activities=[
                mock_download,
                mock_work,
                mock_cleanup,
            ],
        )
        for queue in task_queue_workers
    ]

    # Should execute all fine
    # p(pass| should fail) = 0.333 ^ (n_workers * n_iters)~ 6e-8
    workflow_ids = [str(uuid.uuid4()) for _ in range(5)]
    async with worker_distribution, worker_1, worker_2, worker_3:
        for workflow_id in workflow_ids:
            result = await client.execute_workflow(
                tasks.FileProcessing.run,
                id=workflow_id,
                task_queue=task_queue_name_distribution,
            )
            assert result == CHECKSUM
    # Check all events take place on the same random worker
    workflow_executions = {
        check_sticky_activity_count(
            item.to_json_dict()["events"], task_queue_name_distribution
        )
        async for item in client.list_workflows().map_histories()
    }

    # Each history has only a single sticky worker associated
    assert workflow_executions == {1}
