import asyncio
from datetime import timedelta

from temporalio import activity, workflow

from dan.utils.client import start_workflow


@activity.defn
async def my_activity(name: str) -> str:
    return f"Hello, {name}!"


activities = [my_activity]


@workflow.defn
class Workflow:
    def __init__(self):
        self.received_signal = False
        self.received_update = False

    @workflow.run
    async def run(self) -> str:
        await workflow.wait_condition(
            lambda: self.received_signal and self.received_update
        )
        return "workflow-result"

    @workflow.signal
    def my_signal(self) -> None:
        self.received_signal = True

    @workflow.update
    async def my_update(self) -> None:
        await workflow.execute_activity(
            my_activity, "update", start_to_close_timeout=timedelta(seconds=10)
        )
        self.received_update = True


async def main():
    wf_handle = await start_workflow(Workflow.run)
    print("workflow handle:", wf_handle)
    await wf_handle.signal(Workflow.my_signal)
    await wf_handle.execute_update(Workflow.my_update)
    print("workflow result:", await wf_handle.result())


if __name__ == "__main__":
    asyncio.run(main())
