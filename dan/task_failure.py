import asyncio
import datetime
from datetime import timedelta
from functools import partial

from temporalio import common, workflow
from temporalio.client import Client
from temporalio.exceptions import ApplicationError
from temporalio.worker import UnsandboxedWorkflowRunner, Worker

wid = __file__
tq = "tq"

task_fails_counter = 0


@workflow.defn
class Workflow:
    def __init__(self) -> None:
        self.am_done = False

    @workflow.run
    async def run(self) -> str:
        await workflow.wait_condition(lambda: self.am_done)
        return "Hello, World!"

    @workflow.update
    async def do_update(self):
        global task_fails_counter
        if task_fails_counter < 2:
            task_fails_counter += 1
            raise RuntimeError("I'll fail task")
        else:
            raise ApplicationError("I'll fail update")

    @workflow.update
    async def throw_or_done(self, do_throw: bool):
        self.am_done = True

    @throw_or_done.validator
    def the_validator(self, do_throw: bool):
        if do_throw:
            raise RuntimeError("This will fail validation, not task")


print = partial(print, file=open("/tmp/log", "a"), flush=True)


async def main():
    client = await Client.connect("localhost:7233")
    async with Worker(
        client,
        task_queue=tq,
        workflows=[Workflow],
        workflow_runner=UnsandboxedWorkflowRunner(),
    ):
        t0 = datetime.datetime.now()
        print("🟧 starting workflow")
        handle = await client.start_workflow(
            Workflow.run,
            id=wid,
            task_queue=tq,
            task_timeout=timedelta(seconds=7),
            id_reuse_policy=common.WorkflowIDReusePolicy.TERMINATE_IF_RUNNING,
        )
        t1 = datetime.datetime.now()
        print(f"🟧 start_workflow succeeded in {(t1 - t0).total_seconds()}s")
        try:
            await handle.execute_update(Workflow.do_update)
            raise AssertionError("unreachable")
        except Exception as err:
            t2 = datetime.datetime.now()
            print(
                f"🟥 {err.__class__.__name__}({err}) after {(t2 - t1).total_seconds()}s"
            )

        t3 = datetime.datetime.now()
        try:
            await handle.execute_update(Workflow.throw_or_done, True)
            raise AssertionError("unreachable")
        except Exception as err:
            t4 = datetime.datetime.now()
            print(
                f"🟥 Rejection of wf release, {err.__class__.__name__}({err}) after {(t4 - t3).total_seconds()}s"
            )

        t5 = datetime.datetime.now()
        await handle.execute_update(Workflow.throw_or_done, False)
        t6 = datetime.datetime.now()
        print(
            f"🟩 Acceptance of wf release update succeeded after {(t6 - t5).total_seconds()}s"
        )
        await handle.result()
        global task_fails_counter
        assert task_fails_counter == 2


if __name__ == "__main__":
    t0 = datetime.datetime.now()
    asyncio.run(main())
    t1 = datetime.datetime.now()
    print(f"script exiting after {(t1 - t0).total_seconds()}s")
