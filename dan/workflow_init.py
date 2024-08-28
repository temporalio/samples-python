import asyncio
import traceback

from temporalio import workflow
from utils import start_workflow


@workflow.defn
class Workflow:
    def __init__(self) -> None:
        stack = traceback.extract_stack()
        formatted_stack = traceback.format_list(stack)
        for line in formatted_stack:
            print(line.strip())

    @workflow.run
    async def run(self) -> str:
        return "workflow-result"


async def main():
    wf_handle = await start_workflow(Workflow.run)
    print("workflow handle:", wf_handle)
    print("workflow result:", await wf_handle.result())


if __name__ == "__main__":
    asyncio.run(main())
