import asyncio
from datetime import timedelta

from opentelemetry import trace
from temporalio import activity, workflow
from temporalio.worker import Replayer

import dan.utils.client
from dan import utils
from dan.constants import WORKFLOW_ID


@activity.defn
async def test_activity() -> None:
    return


@workflow.defn
class Workflow:
    def __init__(self) -> None:
        self.running_count = 0
        self.state = "stopped"
        self._done = False

    @workflow.run
    async def run(self) -> None:
        await workflow.wait_condition(lambda: self._done)

    @workflow.signal
    async def start(self) -> None:
        await self.run_one()

    @workflow.update
    async def resume(self) -> None:
        if self.state == "running":
            return
        await self.run_one()

    @workflow.signal
    async def done(self) -> None:
        self._done = True

    async def run_one(self):
        self.running_count += 1
        self.state = "running"
        await workflow.execute_activity(
            test_activity,
            start_to_close_timeout=timedelta(seconds=1),
        )
        self.running_count -= 1
        if self.running_count == 0:
            self.state = "stopped"


activities = [test_activity]


async def starter():
    client = await utils.connect()
    workflow_handle = await dan.utils.client.start_workflow(Workflow.run, client=client)
    await workflow_handle.signal(Workflow.start)
    await asyncio.sleep(5)
    await workflow_handle.execute_update(Workflow.resume)
    await workflow_handle.signal(Workflow.done)
    await workflow_handle.result()

    provider = trace.get_tracer_provider()
    tracer = provider.get_tracer(__name__)

    with tracer.start_as_current_span("Replaying") as span:
        span.add_event("Listing workflows")
        workflows = client.list_workflows(f"WorkflowId = '{WORKFLOW_ID}'")
        span.add_event("Mapping histories")
        histories = workflows.map_histories()
        span.add_event("Replaying")
        replayer = Replayer(workflows=[Workflow])
        await replayer.replay_workflows(histories)


if __name__ == "__main__":
    asyncio.run(starter())
