import uuid
from pathlib import Path
from unittest import mock

import pytest
from temporalio import activity
from temporalio.client import Client
from temporalio.worker import Worker

from activity_sticky_queues import tasks

RETURNED_PATH = "valid/path"
tasks._get_delay_secs = mock.MagicMock(return_value=0.0001)
tasks._get_local_path = mock.MagicMock(return_value=Path(RETURNED_PATH))


async def test_download_activity():
    worker_id = "an-id"
    workflow_uuid = "uuid"
    want = "/".join([RETURNED_PATH, worker_id, workflow_uuid])

    details = tasks.DownloadObj("tdd.com", worker_id, workflow_uuid)
    with mock.patch.object(tasks, "write_file") as mock_write:
        response = await tasks.download_file_to_worker_filesystem(details)
    assert response == want
    mock_write.assert_called_once()


async def test_processing_activity():
    file_contents = b"contents"
    want = tasks.process_file_contents(file_contents)

    with mock.patch.object(tasks, "read_file", return_value=file_contents):
        response = await tasks.work_on_file_in_worker_filesystem(RETURNED_PATH)
    assert response == want


async def test_clean_up_activity():
    with mock.patch.object(tasks, "delete_file") as mock_delete:
        await tasks.clean_up_file_from_worker_filesystem(RETURNED_PATH)
    mock_delete.assert_called_once_with(RETURNED_PATH)
