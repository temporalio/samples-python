import asyncio
import random
from dataclasses import dataclass
from datetime import timedelta
from hashlib import md5
from pathlib import Path
from typing import Any, Callable, Coroutine, List

from temporalio import activity, workflow

TIME_DELAY = 3.0
LOCAL_PATH = Path(__file__).parent / "demo_fs"


@dataclass
class DownloadObj:
    url: str
    unique_worker_id: str
    workflow_uuid: str


@activity.defn
async def get_available_task_queue() -> str:
    """Just a stub for typedworkflow invocation."""
    raise NotImplementedError


@activity.defn
async def download_file_to_worker_filesystem(details: DownloadObj) -> str:
    """Simulates downloading a file to a local filesystem"""
    # FS ops
    directory = LOCAL_PATH / details.unique_worker_id
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / details.workflow_uuid

    activity.logger.info(f"Downloading ${details.url} and saving to ${path}")

    # Here is where the real download code goes. Developers should be careful
    # not to block an async activity. If there are concerns about blocking download
    # or disk IO, developers should use loop.run_in_executor or change this activity
    # to be synchronous. Also like for all non-immediate activities, be sure to
    # heartbeat during download.

    await asyncio.sleep(TIME_DELAY)
    body = "downloaded body"

    with open(path, "w") as handle:
        handle.write(body)
    return str(path)


@activity.defn
async def work_on_file_in_worker_filesystem(path: str) -> str:
    """Processing the file, in this case identical MD5 hashes"""
    with open(path, "rb") as handle:
        content = handle.read()
    checksum = md5(content).hexdigest()
    await asyncio.sleep(TIME_DELAY)
    activity.logger.info(f"Did some work on {path}, checksum {checksum}")
    return checksum


@activity.defn
async def clean_up_file_from_worker_filesystem(path: str) -> None:
    """Deletes the file created in the first activity, but leaves the folder"""
    await asyncio.sleep(TIME_DELAY)
    activity.logger.info(f"Removing {path}")
    Path(path).unlink()


@workflow.defn
class FileProcessing:
    @workflow.run
    async def run(self) -> str:
        """Workflow implementing the basic file processing example.

        First, a worker is selected randomly. This is the "sticky worker" on which
        the workflow runs. This consists of a file download and some processing task,
        with a file cleanup if an error occurs.
        """
        workflow.logger.info("Searching for available worker")
        unique_worker_task_queue = await workflow.execute_activity(
            activity="get_available_task_queue",
            start_to_close_timeout=timedelta(seconds=10),
        )
        workflow.logger.info(f"Matching workflow to worker {unique_worker_task_queue}")

        download_params = DownloadObj(
            url="http://temporal.io",
            unique_worker_id=unique_worker_task_queue,
            workflow_uuid=str(workflow.uuid4()),
        )

        download_path = await workflow.execute_activity(
            download_file_to_worker_filesystem,
            download_params,
            start_to_close_timeout=timedelta(seconds=10),
            task_queue=unique_worker_task_queue,
        )

        checksum = "failed execution"  # Sentinel value
        try:
            checksum = await workflow.execute_activity(
                work_on_file_in_worker_filesystem,
                download_path,
                start_to_close_timeout=timedelta(seconds=10),
                task_queue=unique_worker_task_queue,
            )
        finally:
            await workflow.execute_activity(
                clean_up_file_from_worker_filesystem,
                download_path,
                start_to_close_timeout=timedelta(seconds=10),
                task_queue=unique_worker_task_queue,
            )
        return checksum
