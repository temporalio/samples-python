import asyncio
import logging
from datetime import timedelta

from temporalio import activity, common, workflow
from temporalio.client import Client, WorkflowHandle
from temporalio.worker import Worker

# Problem: You have the buggy workflow below. You need to fix it so that the workflow state is no
# longer garbled due to interleaving of the handler with the main workflow.
#
# Solution 1: Use a sync handler and process the message in the main workflow coroutine.
#
# Solution 2: Await a custom “handler complete” condition.


class WorkflowBase:
    def __init__(self) -> None:
        self.letters = []

    async def do_multiple_async_tasks_that_mutate_workflow_state(self, text: str):
        for i in range(len(text)):
            letter = await workflow.execute_activity(
                get_letter,
                args=[text, i],
                start_to_close_timeout=timedelta(seconds=10),
            )
            self.letters.append(letter)


@workflow.defn
class AccumulateLettersIncorrect(WorkflowBase):
    """
    This workflow implementation is incorrect: the handler execution interleaves with the main
    workflow coroutine.
    """

    def __init__(self) -> None:
        super().__init__()
        self.handler_started = False
        self.handler_finished = False

    @workflow.run
    async def run(self) -> str:
        await workflow.wait_condition(lambda: self.handler_started)
        await self.do_multiple_async_tasks_that_mutate_workflow_state(
            "world!"
        )  # Bug: handler and main wf are now interleaving

        await workflow.wait_condition(lambda: self.handler_finished)
        return "".join(self.letters)

    @workflow.update
    async def update_that_does_multiple_async_tasks_that_mutate_workflow_state(
        self, text: str
    ):
        self.handler_started = True
        await self.do_multiple_async_tasks_that_mutate_workflow_state(text)
        self.handler_finished = True


@workflow.defn
class AccumulateLettersCorrect1(WorkflowBase):
    """
    Solution 1: sync handler enqueues work; splice work into the main wf coroutine so that it cannot
    interleave with work of main wf coroutine.
    """

    def __init__(self) -> None:
        super().__init__()
        self.handler_text = asyncio.Future[str]()
        self.handler_finished = False

    @workflow.run
    async def run(self) -> str:
        handler_input = await self.handler_text
        await self.do_multiple_async_tasks_that_mutate_workflow_state(handler_input)
        await self.do_multiple_async_tasks_that_mutate_workflow_state("world!")
        await workflow.wait_condition(lambda: self.handler_finished)
        return "".join(self.letters)

    # Note: sync handler
    @workflow.update
    def update_that_does_multiple_async_tasks_that_mutate_workflow_state(
        self, text: str
    ):
        self.handler_text.set_result(text)
        self.handler_finished = True


@workflow.defn
class AccumulateLettersCorrect2(WorkflowBase):
    """
    Solution 2: async handler notifies when complete; main wf coroutine waits for this to avoid
    interleaving its own work.
    """

    def __init__(self) -> None:
        super().__init__()
        self.handler_finished = False

    @workflow.run
    async def run(self) -> str:
        await workflow.wait_condition(lambda: self.handler_finished)
        await self.do_multiple_async_tasks_that_mutate_workflow_state("world!")
        return "".join(self.letters)

    @workflow.update
    async def update_that_does_multiple_async_tasks_that_mutate_workflow_state(
        self, text: str
    ):
        await self.do_multiple_async_tasks_that_mutate_workflow_state(text)
        self.handler_finished = True


@activity.defn
async def get_letter(text: str, i: int) -> str:
    return text[i]


async def app(wf: WorkflowHandle):
    await wf.execute_update(
        AccumulateLettersCorrect1.update_that_does_multiple_async_tasks_that_mutate_workflow_state,
        args=["Hello "],
    )
    print(await wf.result())


async def main():
    client = await Client.connect("localhost:7233")

    async with Worker(
        client,
        task_queue="tq",
        workflows=[
            AccumulateLettersIncorrect,
            AccumulateLettersCorrect1,
            AccumulateLettersCorrect2,
        ],
        activities=[get_letter],
    ):
        for wf in [
            AccumulateLettersIncorrect,
            AccumulateLettersCorrect1,
            AccumulateLettersCorrect2,
        ]:
            handle = await client.start_workflow(
                wf.run,
                id="wid",
                task_queue="tq",
                id_reuse_policy=common.WorkflowIDReusePolicy.TERMINATE_IF_RUNNING,
            )
            await app(handle)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
