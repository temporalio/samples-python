import asyncio
import uuid
from datetime import timedelta  # noqa
from typing import Any

from temporalio import activity, workflow
from temporalio.client import Client
from temporalio.worker import Worker


@activity.defn
async def exec_activity(input: str) -> Any:
    namespace = {}
    exec(input, globals(), namespace)
    return await namespace["__activity__"]()


@workflow.defn
class ExecWorkflow:
    @workflow.run
    async def run(self, input: str) -> Any:
        namespace = {}
        exec(input, globals(), namespace)
        return await namespace["__workflow__"]()


async def main():
    client = await Client.connect("localhost:7233")
    async with Worker(
        client,
        task_queue="hello-exec-task-queue",
        workflows=[ExecWorkflow],
        activities=[exec_activity],
    ):
        activity_code_from_llm = """
async def __activity__():
    await asyncio.sleep(1)
    return 1 + 1
"""

        workflow_code_from_llm = f"""
async def __workflow__():
    return await workflow.execute_activity(
        exec_activity,
        '''{activity_code_from_llm}''',
        start_to_close_timeout=timedelta(seconds=10),
    )
"""
        result = await client.execute_workflow(
            ExecWorkflow.run,
            workflow_code_from_llm,
            id=str(uuid.uuid4()),
            task_queue="hello-exec-task-queue",
        )
        print(result)


if __name__ == "__main__":
    asyncio.run(main())
