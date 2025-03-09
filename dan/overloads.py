import asyncio
from typing import cast

from opentelemetry.sdk.trace import Tracer
from temporalio import common, workflow
from temporalio_xray import create_tracer_provider

from dan.utils import connect

provider = create_tracer_provider("Workflow")
tracer = cast(Tracer, provider.get_tracer(__name__))


@workflow.defn
class Workflow:
    @workflow.run
    async def run(self, a: int) -> int:
        return a + 1


async def main():
    client = await connect()
    h = await client.start_workflow(
        "Workflow",
        args=[7],
        id="wid",
        task_queue="tq",
        id_conflict_policy=common.WorkflowIDConflictPolicy.TERMINATE_EXISTING,
    )
    print(await h.result())


if __name__ == "__main__":
    asyncio.run(main())
