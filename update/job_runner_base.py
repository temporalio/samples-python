import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging
from typing import Optional

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


@workflow.defn
class JobRunner:
    """
    Jobs must be executed in order dictated by job dependency graph (see `job.depends_on`) and
    not before `job.after_time`.
    """

    @workflow.run
    async def run(self):
        await workflow.wait_condition(
            lambda: workflow.info().is_continue_as_new_suggested()
        )
        workflow.continue_as_new()

    @workflow.update
    async def run_shell_script_job(self, job: Job) -> JobOutput:
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
