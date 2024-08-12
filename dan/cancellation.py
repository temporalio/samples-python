import asyncio
from typing import NoReturn

from temporalio import workflow
from utils import print, start_workflow


@workflow.defn
class Workflow:
    @workflow.run
    async def run(self) -> NoReturn:
        try:
            await workflow.wait_condition(lambda: False)
        except asyncio.CancelledError:
            print("[blue]caught CancelledError[/blue]")


async def main():
    wf_handle = await start_workflow(Workflow.run)
    await wf_handle.cancel()
    print("[green]done[/green]")


if __name__ == "__main__":
    asyncio.run(main())
