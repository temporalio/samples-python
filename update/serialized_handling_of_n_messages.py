import asyncio
import logging
from asyncio import Future
from collections import deque
from datetime import timedelta

from temporalio import activity, common, workflow
from temporalio.client import Client, WorkflowHandle
from temporalio.worker import Worker

Arg = str
Result = str

# Problem:
# -------
# - Your workflow receives an unbounded number of updates.
# - Each update must be processed by calling two activities.
# - The next update may not start processing until the previous has completed.

# Solution:
# --------
# Enqueue updates, and process items from the queue in a single coroutine (the main workflow
# coroutine).

# Discussion:
# ----------
# The queue is used because Temporal's async update & signal handlers will interleave if they
# contain multiple yield points. An alternative would be to use standard async handler functions,
# with handling being done with an asyncio.Lock held. The queue approach would be necessary if we
# need to process in an order other than arrival.


@workflow.defn
class MessageProcessor:

    @workflow.run
    async def run(self):
        self.queue = deque[tuple[Arg, Future[Result]]]()
        while True:
            await workflow.wait_condition(lambda: len(self.queue) > 0)
            while self.queue:
                arg, fut = self.queue.popleft()
                fut.set_result(await self.process_task(arg))
            if workflow.info().is_continue_as_new_suggested():
                # Footgun: If we don't let the event loop tick, then CAN will end the workflow
                # before the update handler is notified that the result future has completed.
                # See https://github.com/temporalio/features/issues/481
                await asyncio.sleep(0)  # Let update handler complete
                print("CAN")
                return workflow.continue_as_new()

    # Note: handler must be async if we are both enqueuing, and returning an update result
    # => We could add SDK APIs to manually complete updates.
    @workflow.update
    async def add_task(self, arg: Arg) -> Result:
        # Footgun: handler must wait for workflow initialization
        # See https://github.com/temporalio/features/issues/400
        await workflow.wait_condition(lambda: hasattr(self, "queue"))
        fut = Future[Result]()
        self.queue.append((arg, fut))  # Note: update validation gates enqueue
        return await fut

    async def process_task(self, arg):
        t1, t2 = [
            await workflow.execute_activity(
                get_current_time, start_to_close_timeout=timedelta(seconds=10)
            )
            for _ in range(2)
        ]
        return f"{arg}-result-{t1}-{t2}"


time = 0


@activity.defn
async def get_current_time() -> int:
    global time
    time += 1
    return time


async def app(wf: WorkflowHandle):
    for i in range(20):
        print(f"app(): sending update {i}")
        result = await wf.execute_update(MessageProcessor.add_task, f"arg {i}")
        print(f"app(): {result}")


async def main():
    client = await Client.connect("localhost:7233")

    async with Worker(
        client,
        task_queue="tq",
        workflows=[MessageProcessor],
        activities=[get_current_time],
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
