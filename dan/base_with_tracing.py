import asyncio
import os

import xray
from temporalio import workflow

from dan.utils.client import start_workflow


@workflow.defn
class Workflow:
    @workflow.run
    async def run(self) -> str:
        if os.getenv("TRACING"):
            print("🩻")
            with xray.start_as_current_span(
                xray.Actor.WORKFLOW_USER,
                name="WorkflowInit",
                workflow_id=workflow.info().workflow_id,
                request_payload="{}",
            ) as span:
                span.add_event("hello from workflow init")
        return "workflow-result"


async def main():
    wf_handle = await start_workflow(Workflow.run)
    print("workflow handle:", wf_handle)
    print("workflow result:", await wf_handle.result())


if __name__ == "__main__":
    asyncio.run(main())
