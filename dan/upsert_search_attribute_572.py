import asyncio
from datetime import datetime

from temporalio import workflow
from temporalio.common import SearchAttributeKey
from utils import start_workflow

# https://github.com/temporalio/sdk-python/issues/572


@workflow.defn
class Workflow:
    @workflow.run
    async def run(self) -> str:
        t = datetime.fromisoformat("2024-07-05T15:43:07.875302")
        k = SearchAttributeKey.for_datetime("checkout_time")
        u = k.value_set(t)
        workflow.upsert_search_attributes([u])
        return "workflow-result"


async def main():
    wf_handle = await start_workflow(Workflow.run)
    print("workflow result:", await wf_handle.result())


if __name__ == "__main__":
    asyncio.run(main())
