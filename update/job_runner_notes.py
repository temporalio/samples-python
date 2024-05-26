import asyncio
from asyncio import Future
from collections import deque
from datetime import datetime, timedelta
import logging
from sys import version
from typing import Any, Iterator, Optional, TypedDict, Union

from attr import dataclass
from temporalio import common, workflow, activity
from temporalio.client import Client, WorkflowHandle
from temporalio.worker import Worker


###############################################################################
## SDK internals
##
@dataclass
class Message:
    type: str  # maps to a handler if a matching handler exists
    args: tuple[Any]  # deserialized arg payloads
    # Can expose other update/signal metadata
    received_at: datetime
    client_identity: str

    async def handle(self):
        await workflow.call_handler(self.type, *self.args)


@dataclass
class Signal(Message):
    pass


@dataclass
class Update(Message):
    id: str  # the update ID


#
# Raw incoming workflow events
#
# The incoming event stream contains newly delivered updates and signals. Perhaps
# ContinueAsNewSuggested could also be an event.
#
# We could have "UpdateReceived" as the incoming event, with UpdateAccepted/UpdateRejected emitted
# later. However, An alternative is that the SDK executes the update validators immediately, before
# the user has a chance to interact with the event stream. We'll adopt that version for now, since
# it involves fewer event types.
@dataclass
class SignalReceived:
    signal: Signal


@dataclass
class UpdateRejected:
    update: Update


@dataclass
class UpdateAccepted:
    update: Update


@dataclass
class ContinueAsNewSuggested:
    pass


IncomingWorkflowEvent = Union[
    UpdateAccepted, UpdateRejected, SignalReceived, ContinueAsNewSuggested
]


def workflow_incoming_event_stream() -> Iterator[IncomingWorkflowEvent]: ...


setattr(workflow, "incoming_event_stream", workflow_incoming_event_stream)
#
# Other events that are emitted automatically by a running workflow
#


@dataclass
class UpdateCompleted:
    pass


class SignalHandlerReturned:
    # This is tangential to work on updates. Introducing this event would introduce a new concept of
    # "signal-processing finished", which could be used to help users wait for signal processing to
    # finish before CAN / workflow return. The idea is that the event would be emitted when a signal
    # handler returns.
    pass


#
# Events that users can add to the event stream
#


class TimerFired:
    pass


class CustomFutureResolved:
    pass


EventStream = Iterator[
    Union[
        SignalReceived,
        UpdateRejected,
        UpdateAccepted,
        ContinueAsNewSuggested,
        UpdateCompleted,
        SignalHandlerReturned,
        TimerFired,
        CustomFutureResolved,
    ]
]


class Selector:
    def get_event_stream(self) -> EventStream: ...


# By default, a workflow behaves as if it is doing the following:
def handle_incoming_events():
    for ev in workflow.incoming_event_stream():
        match ev:
            case SignalReceived(signal):
                asyncio.create_task(signal.handle())
            case UpdateAccepted(update):
                asyncio.create_task(update.handle())


HandlerType = str
UpdateID = str


# This class is just a toy prototype: this functionality will be implemented on WorkflowInstance in
# the SDK.
class WorkflowInternals:
    def __init__(self):
        self.incoming_event_stream = deque[IncomingWorkflowEvent]()
        self.ready_to_execute_handler: dict[UpdateID, Future[None]] = {}

    def accept_update(self, update: Update):
        # This will be done by the SDK prior to invoking handler, around
        # https://github.com/temporalio/sdk-python/blob/11a97d1ab2ebfe8c973bf396b1e14077ec611e52/temporalio/worker/_workflow_instance.py#L506
        self.incoming_event_stream.append(UpdateAccepted(update))

        # By default, handlers are ready to execute immediately after the update is accepted.
        self.ready_to_execute_handler[update.id] = resolved_future(None)

    async def _wait_until_ready_to_execute(self, update_id: UpdateID):
        await self.ready_to_execute_handler[update_id]


def resolved_future[X](result: X) -> Future[X]:
    fut = Future()
    fut.set_result(result)
    return fut


workflow_internals = WorkflowInternals()

###############################################################################
##
## User's code
##

# A user may want to handle the event stream differently.

# workflow API design must make the following two things convenient for users:
# - DrainBeforeWorkflowCompletion
# - NoInterleaving, optionally with CustomOrder


def make_event_stream() -> EventStream:
    selector = Selector()
    return selector.get_event_stream()


event_stream = make_event_stream()

#
JobId = int
ClusterSlot = str


class Job(TypedDict):
    update_id: UpdateID
    depends_on: list[UpdateID]
    after_time: Optional[int]
    name: str
    run: str
    python_interpreter_version: Optional[str]


class JobOutput(TypedDict):
    status: int
    stdout: str
    stderr: str


@workflow.defn
class JobRunner:

    def __init__(self):
        self.jobs: dict[JobId, Job] = {}

    # Design notes
    # ------------
    # Updates always have handler functions, and an update handler function is still just a normal
    # handler function: it implements the handling logic and the return value.
    #
    # Every workflow will have an underlying event stream. By default, this yields the following
    # events:
    #
    # - UpdateRejected
    # - UpdateAccepted (UpdateEnqueued)
    # - UpdateDequeued
    # - UpdateCompleted
    #
    # The SDK will provide a default implementation of the event stream, looking something like this:

    #
    # The handler will be invoked automatically by the SDK when the underlying event stream yields
    # an UpdateDequeued event for this update ID. The user does not have to know anything about
    # this: by default, handlers are executed before other workflow code, in order of update
    # arrival.

    # The SDK is capable of automatically draining the event stream before workflow return / CAN,
    # including an option for this draining to result in serial execution of the handlers (i.e.
    # waiting for all async work scheduled by the handler to complete before the next handler is
    # invoked, and not allowing the workflow to complete until all such work is complete.) Default
    # behavior TBD.
    #
    # The event stream thus provides a way for users to wait until a specific message handler has
    # completed, or until all message handlers have completed. These can be exposed via convenient
    # `wait_for_X()` APIs, rather than interacting with the raw event stream
    #
    # Furthermore, users can optionally implement the EventStream themselves. This gives them
    # precise control over the ordering of handler invocation with respect to all other workflow
    # events (e.g. other update completions, and custom futures such as timers and
    # workflow.wait_condition).
    #
    # TODO: does handler invocation remain automatic on yielding Dequeue, or is that too magical. An
    # alternative would be for users to be able to call update.handle() on an update object obtained
    # from an event object yielded by the event stream.

    @workflow.update
    async def run_shell_script_job(self, job: Job) -> JobOutput:
        """
        To be executed in order dictated by job dependency graph (see `jobs.depends_on`) and not
        before `job.after_time`.
        """
        ## SDK internals: please pretend this is implemented in the SDK
        await workflow_internals._wait_until_ready_to_execute(job["update_id"])
        ##

        if security_errors := await workflow.execute_activity(
            run_shell_script_security_linter,
            args=[job["run"]],
            start_to_close_timeout=timedelta(seconds=10),
        ):
            return JobOutput(status=1, stdout="", stderr=security_errors)
        job_output = await workflow.execute_activity(
            run_job, args=[job], start_to_close_timeout=timedelta(seconds=10)
        )  # SDK emits UpdateCompleted
        return job_output

    @workflow.update
    async def run_python_job(self, job: Job) -> JobOutput:
        """
        To be executed in order dictated by job dependency graph (see `jobs.depends_on`) and not
        before `job.after_time`.
        """
        ## SDK internals: please pretend this is implemented in the SDK
        await workflow_internals._wait_until_ready_to_execute(job["update_id"])
        ##

        if not await workflow.execute_activity(
            check_python_interpreter_version,
            args=[job["python_interpreter_version"]],
            start_to_close_timeout=timedelta(seconds=10),
        ):
            return JobOutput(
                status=1,
                stdout="",
                stderr=f"Python interpreter version {version} is not available",
            )
        job_output = await workflow.execute_activity(
            run_job, args=[job], start_to_close_timeout=timedelta(seconds=10)
        )  # SDK emits UpdateCompleted
        return job_output

    @run_shell_script_job.validator
    def validate_shell_script_job(self, job: Job):
        ## SDK internals: please pretend this is implemented in the SDK
        workflow_internals.accept_update(
            Update(
                type="run_shell_script_job",
                args=(job,),
                client_identity="some-client-id",
                id=job["update_id"],
                received_at=workflow.now(),
            )
        )
        ##

    @run_python_job.validator
    def validate_python_job(self, job: Job):
        ## SDK internals: please pretend this is implemented in the SDK
        workflow_internals.accept_update(
            Update(
                type="run_python_job",
                args=(job,),
                client_identity="some-client-id",
                id=job["update_id"],
                received_at=workflow.now(),
            )
        )
        ##

    @workflow.run
    async def run(self):
        while not workflow.info().is_continue_as_new_suggested():
            await workflow.wait_condition(lambda: len(self.jobs) > 0)
        workflow.continue_as_new()


@activity.defn
async def run_job(job: Job) -> JobOutput:
    await asyncio.sleep(0.1)
    stdout = f"Ran job {job["name"]} at {datetime.now()}"
    print(stdout)
    return JobOutput(status=0, stdout=stdout, stderr="")


@activity.defn
async def request_cluster_slot(job: Job) -> ClusterSlot:
    await asyncio.sleep(0.1)
    return "cluster-slot-token-abc123"


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
        update_id="1",
        depends_on=[],
        after_time=None,
        name="should-run-first",
        run="echo 'Hello world 1!'",
        python_interpreter_version=None,
    )
    job_2 = Job(
        update_id="2",
        depends_on=["1"],
        after_time=None,
        name="should-run-second",
        run="print('Hello world 2!')",
        python_interpreter_version=None,
    )
    job_2 = await wf.execute_update(JobRunner.run_python_job, job_2)
    job_1 = await wf.execute_update(JobRunner.run_shell_script_job, job_1)


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
            request_cluster_slot,
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
