import asyncio

from temporalio import common, workflow
from temporalio.client import Client, WorkflowUpdateStage
from temporalio.exceptions import ApplicationError
from temporalio.worker import Worker

wid = __file__
tq = "tq"


@workflow.defn
class MainCoroutineExitShouldHavePriorityOverHandlerWorkflow:
    def __init__(self) -> None:
        self.seen_first_signal = False
        self.seen_second_signal = False
        self.should_can = True  # a signal could toggle this

    @workflow.run
    async def run(self):
        await workflow.wait_condition(
            lambda: self.seen_first_signal and self.seen_second_signal
        )

    @workflow.signal
    async def this_signal_always_executes_first(self):
        self.seen_first_signal = True
        if self.should_can:
            workflow.continue_as_new()

    @workflow.signal
    async def this_signal_always_executes_second(self):
        await workflow.wait_condition(lambda: self.seen_first_signal)
        self.seen_second_signal = True
        raise ApplicationError("I don't expect this to be raised if signal 1 did CAN")


@workflow.defn
class SecretDetectorWorkflow:
    def __init__(self) -> None:
        self.data: list[str] = []

    @workflow.run
    async def run(self) -> None:
        await workflow.wait_condition(lambda: False)

    @workflow.signal
    def send_data(self, data: str):
        self.data.append(data)
        self.check_data()

    def check_data(self):
        for d in self.data:
            if d.startswith("<SECRET>"):
                raise ApplicationError("secret detected, shutting down immediately")

    @workflow.update
    async def read_data(self) -> list[str]:
        await workflow.wait_condition(lambda: len(self.data) > 0)
        return self.data


@workflow.defn
class ShutdownImmediatelyWorkflow:
    def __init__(self) -> None:
        self.data: list[str] = []

    @workflow.run
    async def run(self) -> None:
        await workflow.wait_condition(lambda: False)

    @workflow.signal
    async def shutdown_immediately(self):
        self.data.append("immediate shutdown requested")
        raise ApplicationError("immediate shutdown requested")

    @workflow.update
    async def read_data(self) -> list[str]:
        await workflow.wait_condition(lambda: len(self.data) > 0)
        return self.data


async def run_main_coroutine_exit_should_have_priority_over_handler():
    client = await Client.connect("localhost:7233")
    async with Worker(
        client,
        task_queue=tq,
        workflows=[MainCoroutineExitShouldHavePriorityOverHandlerWorkflow],
    ):
        wf_handle = await client.start_workflow(
            MainCoroutineExitShouldHavePriorityOverHandlerWorkflow.run,
            id=wid,
            task_queue=tq,
            id_reuse_policy=common.WorkflowIDReusePolicy.TERMINATE_IF_RUNNING,
        )
        await wf_handle.signal(
            MainCoroutineExitShouldHavePriorityOverHandlerWorkflow.this_signal_always_executes_second
        )
        await wf_handle.signal(
            MainCoroutineExitShouldHavePriorityOverHandlerWorkflow.this_signal_always_executes_first
        )


async def run_secret_detector():
    client = await Client.connect("localhost:7233")
    async with Worker(
        client,
        task_queue=tq,
        workflows=[SecretDetectorWorkflow],
    ):
        wf_handle = await client.start_workflow(
            SecretDetectorWorkflow.run,
            id=wid,
            task_queue=tq,
            id_reuse_policy=common.WorkflowIDReusePolicy.TERMINATE_IF_RUNNING,
        )

        upd_handle = await wf_handle.start_update(
            SecretDetectorWorkflow.read_data,
            wait_for_stage=WorkflowUpdateStage.ACCEPTED,
        )
        await wf_handle.signal(
            SecretDetectorWorkflow.send_data,
            "<SECRET> Updates must not return this! </SECRET>",
        )
        print(await upd_handle.result())


async def run_shutdown_immediately():
    client = await Client.connect("localhost:7233")
    async with Worker(
        client,
        task_queue=tq,
        workflows=[ShutdownImmediatelyWorkflow],
    ):
        wf_handle = await client.start_workflow(
            ShutdownImmediatelyWorkflow.run,
            id=wid,
            task_queue=tq,
            id_reuse_policy=common.WorkflowIDReusePolicy.TERMINATE_IF_RUNNING,
        )

        upd_handle = await wf_handle.start_update(
            ShutdownImmediatelyWorkflow.read_data,
            wait_for_stage=WorkflowUpdateStage.ACCEPTED,
        )
        await wf_handle.signal(ShutdownImmediatelyWorkflow.shutdown_immediately)
        print(await upd_handle.result())


if __name__ == "__main__":
    asyncio.run(run_secret_detector())
