import asyncio
from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
import logging
from typing import Awaitable, Callable, Optional

from temporalio import common, workflow, activity
from temporalio.client import Client, WorkflowHandle
from temporalio.worker import Worker


JobID = str


@dataclass
class Job:
    id: JobID
    depends_on: list[JobID]
    after_time: Optional[int]
    name: str
    run: str
    python_interpreter_version: Optional[str]


@dataclass
class JobOutput:
    status: int
    stdout: str
    stderr: str


class TaskStatus(Enum):
    BLOCKED = 1
    UNBLOCKED = 2


@dataclass
class Task:
    input: Job
    handler: Callable[["JobRunner", Job], Awaitable[JobOutput]]
    status: TaskStatus = TaskStatus.BLOCKED
    output: Optional[JobOutput] = None


@workflow.defn
class JobRunner:
    """
    Jobs must be executed in order dictated by job dependency graph (see `job.depends_on`) and
    not before `job.after_time`.
    """

    def __init__(self) -> None:
        self.task_queue = OrderedDict[JobID, Task]()
        self.completed_tasks = set[JobID]()

    def all_handlers_completed(self):
        # We are considering adding an API like `all_handlers_completed` to SDKs. In this particular
        # case, the user doesn't actually need the new API, since they are forced to track pending
        # tasks in their queue implementation.
        return not self.task_queue

    # Note some undesirable things:
    # 1. The update handler functions have become generic enqueuers; the "real" handler functions
    #    are some other methods that don't have the @workflow.update decorator.
    # 2. The update handler functions have to store a reference to the real handler in the queue.
    # 3. The workflow `run` method is *much* more complicated and bug-prone here, compared to
    #    I1:WaitUntilReadyToExecuteHandler

    @workflow.run
    async def run(self):
        """
        Process all tasks in the queue serially, in the main workflow coroutine.
        """
        # Note: there are many mistakes a user will make while trying to implement this workflow.
        while not (
            workflow.info().is_continue_as_new_suggested()
            and self.all_handlers_completed()
        ):
            await workflow.wait_condition(lambda: bool(self.task_queue))
            for id, task in list(self.task_queue.items()):
                if task.status == TaskStatus.UNBLOCKED:
                    await task.handler(self, task.input)
                    del self.task_queue[id]
                    self.completed_tasks.add(id)
            for id, task in self.task_queue.items():
                if task.status == TaskStatus.BLOCKED and self.ready_to_execute(
                    task.input
                ):
                    task.status = TaskStatus.UNBLOCKED
        workflow.continue_as_new()

    def ready_to_execute(self, job: Job) -> bool:
        if not set(job.depends_on) <= self.completed_tasks:
            return False
        if after_time := job.after_time:
            if float(after_time) > workflow.now().timestamp():
                return False
        return True

    async def _enqueue_job_and_wait_for_result(
        self, job: Job, handler: Callable[["JobRunner", Job], Awaitable[JobOutput]]
    ) -> JobOutput:
        task = Task(job, handler)
        self.task_queue[job.id] = task
        await workflow.wait_condition(lambda: task.output is not None)
        # Footgun: a user might well think that they can record task completion here, but in fact it
        # deadlocks.
        # self.completed_tasks.add(job.id)
        assert task.output
        return task.output

    @workflow.update
    async def run_shell_script_job(self, job: Job) -> JobOutput:
        return await self._enqueue_job_and_wait_for_result(
            job, JobRunner._actually_run_shell_script_job
        )

    async def _actually_run_shell_script_job(self, job: Job) -> JobOutput:
        if security_errors := await workflow.execute_activity(
            run_shell_script_security_linter,
            args=[job.run],
            start_to_close_timeout=timedelta(seconds=10),
        ):
            return JobOutput(status=1, stdout="", stderr=security_errors)
        job_output = await workflow.execute_activity(
            run_job, args=[job], start_to_close_timeout=timedelta(seconds=10)
        )
        return job_output

    @workflow.update
    async def run_python_job(self, job: Job) -> JobOutput:
        return await self._enqueue_job_and_wait_for_result(
            job, JobRunner._actually_run_python_job
        )

    async def _actually_run_python_job(self, job: Job) -> JobOutput:
        if not await workflow.execute_activity(
            check_python_interpreter_version,
            args=[job.python_interpreter_version],
            start_to_close_timeout=timedelta(seconds=10),
        ):
            return JobOutput(
                status=1,
                stdout="",
                stderr=f"Python interpreter version {job.python_interpreter_version} is not available",
            )
        job_output = await workflow.execute_activity(
            run_job, args=[job], start_to_close_timeout=timedelta(seconds=10)
        )
        return job_output


@activity.defn
async def run_job(job: Job) -> JobOutput:
    await asyncio.sleep(0.1)
    stdout = f"Ran job {job.name} at {datetime.now()}"
    print(stdout)
    return JobOutput(status=0, stdout=stdout, stderr="")


@activity.defn
async def run_shell_script_security_linter(code: str) -> str:
    # The user's organization requires that all shell scripts pass an in-house linter that checks
    # for shell scripting constructions deemed insecure.
    await asyncio.sleep(0.1)
    return ""


@activity.defn
async def check_python_interpreter_version(version: str) -> bool:
    await asyncio.sleep(0.1)
    version_is_available = True
    return version_is_available


async def app(wf: WorkflowHandle):
    job_1 = Job(
        id="1",
        depends_on=[],
        after_time=None,
        name="should-run-first",
        run="echo 'Hello world 1!'",
        python_interpreter_version=None,
    )
    job_2 = Job(
        id="2",
        depends_on=["1"],
        after_time=None,
        name="should-run-second",
        run="print('Hello world 2!')",
        python_interpreter_version=None,
    )
    await asyncio.gather(
        wf.execute_update(JobRunner.run_python_job, job_2),
        wf.execute_update(JobRunner.run_shell_script_job, job_1),
    )


async def main():
    client = await Client.connect("localhost:7233")
    async with Worker(
        client,
        task_queue="tq",
        workflows=[JobRunner],
        activities=[
            run_job,
            run_shell_script_security_linter,
            check_python_interpreter_version,
        ],
    ):
        wf = await client.start_workflow(
            JobRunner.run,
            id="wid",
            task_queue="tq",
            id_reuse_policy=common.WorkflowIDReusePolicy.TERMINATE_IF_RUNNING,
        )
        await app(wf)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
