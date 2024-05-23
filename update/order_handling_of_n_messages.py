import asyncio
import logging
import random
from typing import Optional

from temporalio import common, workflow
from temporalio.client import Client, WorkflowHandle
from temporalio.worker import Worker

Payload = str
SerializedQueueState = tuple[int, list[tuple[int, Payload]]]


class OrderedQueue:
    def __init__(self):
        self._futures = {}
        self.head = 0
        self.lock = asyncio.Lock()

    def add(self, item: Payload, position: int):
        fut = self._futures.setdefault(position, asyncio.Future())
        if not fut.done():
            fut.set_result(item)
        else:
            workflow.logger.warn(f"duplicate message for position {position}")

    async def next(self) -> Payload:
        async with self.lock:
            payload = await self._futures.setdefault(self.head, asyncio.Future())
            # Note: user must delete the payload to avoid unbounded memory usage
            del self._futures[self.head]
            self.head += 1
            return payload

    def serialize(self) -> SerializedQueueState:
        payloads = [(i, fut.result()) for i, fut in self._futures.items() if fut.done()]
        return (self.head, payloads)

    # This is bad, but AFAICS it's the best we can do currently until we have a workflow init
    # functionality in all SDKs (https://github.com/temporalio/features/issues/400). Currently the
    # problem is: if a signal/update handler is sync, then it cannot wait for anything in the main
    # wf coroutine. After CAN, a message may arrive in the first WFT, but the sync handler cannot
    # wait for wf state to be initialized. So we are forced to update an *existing* queue with the
    # carried-over state.
    def update_from_serialized_state(self, serialized_state: SerializedQueueState):
        head, payloads = serialized_state
        self.head = head
        for i, p in payloads:
            if i in self._futures:
                workflow.logger.error(f"duplicate message {i} encountered when deserializing state carried over CAN")
            else:
                self._futures[i] = resolved_future(p)


def resolved_future[X](x: X) -> asyncio.Future[X]:
    fut = asyncio.Future[X]()
    fut.set_result(x)
    return fut



@workflow.defn
class MessageProcessor:
    def __init__(self) -> None:
        self.queue = OrderedQueue()

    @workflow.run
    async def run(self, serialized_queue_state: Optional[SerializedQueueState] = None):
        # Initialize workflow state after CAN. Note that handler is sync, so it cannot wait for
        # workflow initialization.
        if serialized_queue_state:
            self.queue.update_from_serialized_state(serialized_queue_state)
        while True:
            workflow.logger.info(f"waiting for msg {self.queue.head + 1}")
            payload = await self.queue.next()
            workflow.logger.info(payload)
            if workflow.info().is_continue_as_new_suggested():
                workflow.logger.info("CAN")
                workflow.continue_as_new(args=[self.queue.serialize()])

    # Note: sync handler
    @workflow.update
    def process_message(self, sequence_number: int, payload: Payload):
        self.queue.add(payload, sequence_number)


async def app(wf: WorkflowHandle):
    sequence_numbers = list(range(100))
    random.shuffle(sequence_numbers)
    for i in sequence_numbers:
        print(f"sending update {i}")
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
        await asyncio.gather(app(wf), wf.result())


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
