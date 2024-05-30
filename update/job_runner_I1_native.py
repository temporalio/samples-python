import asyncio
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta
import inspect
import logging
from typing import Callable, Optional, Type

from temporalio import common, workflow, activity
from temporalio.client import Client, WorkflowHandle
from temporalio.worker import Worker

# This file contains a proposal for how the Python SDK could provide I1:WaitUntilReadyToExecute
# functionality to help users defer processing, control interleaving of handler coroutines, and
# ensure processing is complete before workflow completion.


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


##
## SDK internals toy prototype
##

# TODO: use generics to satisfy serializable interface. Faking for now by using user-defined classes.
I = Job
O = JobOutput

UpdateID = str
Workflow = Type


@dataclass
class Update:
    id: UpdateID
    arg: I


_sdk_internals_pending_tasks_count = 0
_sdk_internals_handler_mutex = asyncio.Lock()


def _sdk_internals_all_handlers_completed(self) -> bool:
    # We are considering adding an API like `all_handlers_completed` to SDKs. We've added
    # self._pending tasks to this workflow in lieu of it being built into the SDKs.
    return not _sdk_internals_pending_tasks_count


@asynccontextmanager
async def _sdk_internals__track_pending__wait_until_ready__serialize_execution(
    execute_condition: Callable[[], bool]
):
    global _sdk_internals_pending_tasks_count
    _sdk_internals_pending_tasks_count += 1
    await workflow.wait_condition(execute_condition)
    await _sdk_internals_handler_mutex.acquire()
    try:
        yield
    finally:
        _sdk_internals_handler_mutex.release()
        _sdk_internals_pending_tasks_count -= 1


class SDKInternals:
    # Here, the SDK is wrapping the user's update handlers with the required wait-until-ready,
    # pending tasks tracking, and synchronization functionality. This is a fake implementation: the
    # real implementation will automatically inspect and wrap the user's declared update handlers.

    def ready_to_execute(self, update: Update) -> bool:
        # Overridden by users who wish to control order of execution
        return True

    @workflow.update
    async def run_shell_script_job(self, arg: I) -> O:
        handler = getattr(self, "_" + inspect.currentframe().f_code.co_name)
        async with _sdk_internals__track_pending__wait_until_ready__serialize_execution(
            lambda: self.ready_to_execute(Update(arg.id, arg))
        ):
            return await handler(arg)

    @workflow.update
    async def run_python_job(self, arg: I) -> O:
        handler = getattr(self, "_" + inspect.currentframe().f_code.co_name)
        async with _sdk_internals__track_pending__wait_until_ready__serialize_execution(
            lambda: self.ready_to_execute(Update(arg.id, arg))
        ):
            return await handler(arg)


# Monkey-patch proposed new public API
setattr(workflow, "all_handlers_completed", _sdk_internals_all_handlers_completed)
setattr(workflow, "Update", Update)
##
## END SDK internals prototype
##


@workflow.defn
class JobRunner(SDKInternals):
    """
    Jobs must be executed in order dictated by job dependency graph (see `job.depends_on`) and
    not before `job.after_time`.
    """

    def __init__(self) -> None:
        self.completed_tasks = set[JobID]()

    @workflow.run
    async def run(self):
        await workflow.wait_condition(
            lambda: (
                workflow.info().is_continue_as_new_suggested()
                and workflow.all_handlers_completed()
            )
        )
        workflow.continue_as_new()

    def ready_to_execute(self, update: workflow.Update) -> bool:
        job = update.arg
        if not set(job.depends_on) <= self.completed_tasks:
            return False
        if after_time := job.after_time:
            if float(after_time) > workflow.now().timestamp():
                return False
        return True

    # These are the real handler functions. When we implement SDK support, these will use the
    # decorator form commented out below, and will not use an underscore prefix.

    # @workflow.update(execute_condition=ready_to_execute)
    async def _run_shell_script_job(self, job: Job) -> JobOutput:
        if security_errors := await workflow.execute_activity(
            run_shell_script_security_linter,
            args=[job.run],
            start_to_close_timeout=timedelta(seconds=10),
        ):
            return JobOutput(status=1, stdout="", stderr=security_errors)
        job_output = await workflow.execute_activity(
            run_job, args=[job], start_to_close_timeout=timedelta(seconds=10)
        )
        # FIXME: unbounded memory usage
        self.completed_tasks.add(job.id)
        return job_output

    # @workflow.update(execute_condition=ready_to_execute)
    async def _run_python_job(self, job: Job) -> JobOutput:
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
        # FIXME: unbounded memory usage
        self.completed_tasks.add(job.id)
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
