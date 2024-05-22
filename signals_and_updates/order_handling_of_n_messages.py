import asyncio
import logging
import random

from temporalio import common, workflow
from temporalio.client import Client, WorkflowHandle
from temporalio.worker import Worker

Payload = str


class Queue:
    def __init__(self) -> None:
        self._head = 0
        self._futures: dict[int, asyncio.Future[Payload]] = {}
        self.lock = asyncio.Lock()

    def add(self, item: Payload, position: int):
        fut = self._futures.setdefault(position, asyncio.Future())
        if not fut.done():
            fut.set_result(item)
        else:
            workflow.logger.warn(f"duplicate message for position {position}")

    async def next(self) -> Payload:
        async with self.lock:
            payload = await self._futures.setdefault(self._head, asyncio.Future())
            self._head += 1
            return payload


@workflow.defn
class MessageProcessor:
    def __init__(self) -> None:
        self.queue = Queue()

    @workflow.run
    async def run(self):
        while True:
            payload = await self.queue.next()
            workflow.logger.info(payload)
            if workflow.info().is_continue_as_new_suggested():
                workflow.continue_as_new()

    @workflow.update
    def process_message(self, sequence_number: int, payload: Payload):  # sync handler
        self.queue.add(payload, sequence_number)


async def app(wf: WorkflowHandle):
    sequence_numbers = list(range(10))
    random.shuffle(sequence_numbers)
    for i in sequence_numbers:
        await wf.execute_update(
            MessageProcessor.process_message, args=[i, f"payload {i}"]
        )


async def main():
    client = await Client.connect("localhost:7233")

    async with Worker(
        client,
        task_queue="tq",
        workflows=[MessageProcessor],
    ):
        wf = await client.start_workflow(
            MessageProcessor.run,
            id="wid",
            task_queue="tq",
            id_reuse_policy=common.WorkflowIDReusePolicy.TERMINATE_IF_RUNNING,
        )
        await app(wf)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
