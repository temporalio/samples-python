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
    path: str


async def _get_available_task_queue(available_queues: List[str]) -> str:
    """Randomly assign the job to a queue"""
    return random.choice(available_queues)


@activity.defn
async def download_file_to_worker_filesystem(details: DownloadObj):
    """Simulates downloading a file to a local filesystem"""
    activity.logger.info(f"Downloading ${details.url} and saving to ${details.path}")
    # Here is where the real download code goes
    Path(details.path).parent.mkdir(parents=True, exist_ok=True)
    body = "downloaded body"
    await asyncio.sleep(TIME_DELAY)
    with open(details.path, "w") as handle:
        handle.write(body)


@activity.defn
async def work_on_file_in_worker_filesystem(path: str):
    """Processing the file, in this case identical MD5 hashes"""
    with open(path, "rb") as handle:
        content = handle.read()
    checksum = md5(content).hexdigest()
    await asyncio.sleep(TIME_DELAY)
    activity.logger.info(f"Did some work on {path}, checksum {checksum}")
    return checksum


@activity.defn
async def clean_up_file_from_worker_filesystem(path: str):
    """Deletes the file created in the first activity, but leaves the folder"""
    await asyncio.sleep(TIME_DELAY)
    activity.logger.info(f"Removing {path}")
    Path(path).unlink()


def build_nonsticky_activity(
    task_queue: List[str],
) -> Callable[[], Coroutine[Any, Any, str]]:
    """Closure to allow injection of the queue names"""

    @activity.defn
    async def get_available_task_queue() -> str:
        return await _get_available_task_queue(task_queue)

    return get_available_task_queue


@workflow.defn
class FileProcessing:
    @workflow.run
    async def run(self):
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

        filename = str(workflow.uuid4())
        download_path = str(LOCAL_PATH / unique_worker_task_queue / filename)
        download_params = DownloadObj(url="http://temporal.io", path=download_path)

        checksum = "failed execution"
        await workflow.execute_activity(
            download_file_to_worker_filesystem,
            download_params,
            start_to_close_timeout=timedelta(seconds=10),
            task_queue=unique_worker_task_queue,
        )
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
