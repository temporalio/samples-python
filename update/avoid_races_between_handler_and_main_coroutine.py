import asyncio
import logging
from datetime import timedelta

from temporalio import activity, common, workflow
from temporalio.client import Client, WorkflowHandle
from temporalio.worker import Worker


class WorkflowBase:
    def __init__(self) -> None:
        self.letters = []

    async def get_letters(self, text: str):
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

    @workflow.run
    async def run(self) -> str:
        await workflow.wait_condition(lambda: self.handler_started)
        await self.get_letters(
            "world!"
        )  # Bug: handler and main wf are now interleaving

        await workflow.wait_condition(lambda: len(self.letters) == len("Hello world!"))
        return "".join(self.letters)

    @workflow.update
    async def put_letters(self, text: str):
        self.handler_started = True
        await self.get_letters(text)


@workflow.defn
class AccumulateLettersCorrect1(WorkflowBase):
    def __init__(self) -> None:
        super().__init__()
        self.handler_text = asyncio.Future[str]()

    @workflow.run
    async def run(self) -> str:
        handler_text = await self.handler_text
        await self.get_letters(handler_text)
        await self.get_letters("world!")
        await workflow.wait_condition(lambda: len(self.letters) == len("Hello world!"))
        return "".join(self.letters)

    # Note: sync handler
    @workflow.update
    def put_letters(self, text: str):
        self.handler_text.set_result(text)


@workflow.defn
class AccumulateLettersCorrect2(WorkflowBase):
    def __init__(self) -> None:
        super().__init__()
        self.handler_complete = False

    @workflow.run
    async def run(self) -> str:
        await workflow.wait_condition(lambda: self.handler_complete)
        await self.get_letters("world!")
        await workflow.wait_condition(lambda: len(self.letters) == len("Hello world!"))
        return "".join(self.letters)

    @workflow.update
    async def put_letters(self, text: str):
        await self.get_letters(text)
        self.handler_complete = True


@activity.defn
async def get_letter(text: str, i: int) -> str:
    return text[i]


async def app(wf: WorkflowHandle):
    await wf.execute_update(AccumulateLettersCorrect1.put_letters, args=["Hello "])
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
