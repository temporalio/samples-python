import asyncio
from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
import inspect
import logging
from typing import Awaitable, Callable, Optional, Type

from temporalio import common, workflow, activity
from temporalio.client import Client, WorkflowHandle
from temporalio.worker import Worker


##
## user code
##


JobID = str


class JobStatus(Enum):
    BLOCKED = 1
    UNBLOCKED = 2


@dataclass
class Job:
    id: JobID
    depends_on: list[JobID]
    after_time: Optional[int]
    name: str
    run: str
    python_interpreter_version: Optional[str]
    # TODO: How to handle enums in dataclasses with Temporal's ser/de.
    status_value: int = JobStatus.BLOCKED.value

    @property
    def status(self):
        return JobStatus(self.status_value)

    @status.setter
    def status(self, status: JobStatus):
        self.status_value = status.value


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
    arg: I  # real implementation will support multiple args
    handler: Callable[[Workflow, I], Awaitable[O]]
    output: Optional[O] = None

    @property
    def id(self):
        # In our real implementation the SDK will have native access to the update ID. Currently
        # this example is assuming the user passes it in the update arg.
        return self.arg.id

    async def handle(self, wf: Workflow) -> O:
        # TODO: error-handling
        # TODO: prevent handling an update twice
        update_result = await self.handler(wf, self.arg)
        del workflow.update_queue[self.id]
        return update_result


async def _sdk_internals_enqueue_job_and_wait_for_result(
    arg: I, handler: Callable[[Type, I], Awaitable[O]]
) -> O:
    update = Update(arg, handler)
    workflow.update_queue[update.id] = update
    await workflow.wait_condition(lambda: update.output is not None)
    assert update.output
    return update.output


class SDKInternals:
    # Here, the SDK is wrapping the user's update handlers with the required enqueue-and-wait
    # functionality. This is a fake implementation: the real implementation will automatically
    # inspect and wrap the user's declared update handlers.

    @workflow.update
    async def run_shell_script_job(self, arg: I) -> O:
        handler = getattr(self.__class__, "_" + inspect.currentframe().f_code.co_name)
        return await _sdk_internals_enqueue_job_and_wait_for_result(arg, handler)

    @workflow.update
    async def run_python_job(self, arg: I) -> O:
        handler = getattr(self.__class__, "_" + inspect.currentframe().f_code.co_name)
        return await _sdk_internals_enqueue_job_and_wait_for_result(arg, handler)


# Monkey-patch proposed new public API
setattr(workflow, "update_queue", OrderedDict[UpdateID, Update]())
# The queue-processing style doesn't need an `all_handlers_completed` API: this condition is true
# iff workflow.update_queue is empty.

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
        super().__init__()
        self.completed_tasks = set[JobID]()

    # Note some desirable things:
    # 1. The update handler functions are now "real" handler functions

    # Note some undesirable things:
    # 1. The workflow `run` method is still *much* more complicated and bug-prone here, compared to
    #    I1:WaitUntilReadyToExecuteHandler

    @workflow.run
    async def run(self):
        """
        Process all tasks in the queue serially, in the main workflow coroutine.
        """
        # Note: a user will make mistakes while trying to implement this workflow, due to the
        # unblocking algorithm that this particular example seems to require when implemented via
        # queue-processing in the main workflow coroutine (this example is simpler to implement by
        # making each handler invocation wait until it should execute, and allowing the execution to
        # take place in the handler coroutine, with a mutex held. See job_runner_I1.py and
        # job_runner_I1_native.py)
        while (
            workflow.update_queue or not workflow.info().is_continue_as_new_suggested()
        ):
            await workflow.wait_condition(lambda: bool(workflow.update_queue))
            for id, update in list(workflow.update_queue.items()):
                job = update.arg
                if job.status == JobStatus.UNBLOCKED:
                    # This is how a user manually handles an update. Note that it takes a reference
                    # to the workflow instance, since an update handler has access to the workflow
                    # instance.
                    await update.handle(self)

                    # FIXME: unbounded memory usage; this example use-case needs to know which
                    # updates have completed. Perhaps the real problem here lies with the example,
                    # i.e. the example needs to be made more realistic.
                    self.completed_tasks.add(id)
            for id, update in workflow.update_queue.items():
                job = update.arg
                if job.status == JobStatus.BLOCKED and self.ready_to_execute(job):
                    job.status = JobStatus.UNBLOCKED
        workflow.continue_as_new()

    def ready_to_execute(self, job: Job) -> bool:
        if not set(job.depends_on) <= self.completed_tasks:
            return False
        if after_time := job.after_time:
            if float(after_time) > workflow.now().timestamp():
                return False
        return True

    # These are the real handler functions. When we implement SDK support, these will use the
    # @workflow.update decorator and will not use an underscore prefix.
    # TBD update decorator argument name:
    # queue=True
    # enqueue=True
    # auto=False
    # auto_handle=False
    # manual=True

    # @workflow.update(queue=True)
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
        return job_output

    # @workflow.update(queue=True)
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
