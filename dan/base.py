import asyncio
from datetime import timedelta

from temporalio import activity, workflow

from dan.utils.client import start_workflow


@activity.defn
async def hello_activity() -> str:
    return "activity-result"


@workflow.defn
class Workflow:
    @workflow.run
    async def run(self) -> str:
        return await workflow.execute_activity(
            hello_activity, start_to_close_timeout=timedelta(seconds=10)
        )


activities = [hello_activity]


async def main():
    wf_handle = await start_workflow(Workflow.run)
    print("workflow result:", await wf_handle.result())


if __name__ == "__main__":
    asyncio.run(main())
