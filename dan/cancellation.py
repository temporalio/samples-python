import asyncio
from typing import NoReturn

from temporalio import workflow

from dan.utils import print, start_workflow


@workflow.defn
class Workflow:
    @workflow.run
    async def run(self) -> NoReturn:
        await asyncio.Future()


async def main():
    wf_handle = await start_workflow(Workflow.run)
    await wf_handle.cancel()
    print("[green]done[/green]")


if __name__ == "__main__":
    asyncio.run(main())
