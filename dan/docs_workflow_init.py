import asyncio
from dataclasses import dataclass
from datetime import timedelta

from temporalio import activity, common, workflow
from temporalio import client as cl
from temporalio.client import WorkflowUpdateStage


@dataclass
class MyWorkflowInput:
    name: str


@workflow.defn
class Workflow:
    @workflow.init
    def __init__(self, workflow_input: MyWorkflowInput) -> None:
        self.name_with_title = f"Sir {workflow_input.name}"
        self.title_has_been_checked = False

    @workflow.run
    async def get_greeting(self, workflow_input: MyWorkflowInput) -> str:
        await workflow.wait_condition(lambda: self.title_has_been_checked)
        return f"Hello, {self.name_with_title}"

    @workflow.update
    async def check_title_validity(self) -> bool:
        # 👉 The handler is now guaranteed to see the workflow input
        # after it has been processed by __init__.
        is_valid = await workflow.execute_activity(
            check_title_validity,
            self.name_with_title,
            schedule_to_close_timeout=timedelta(seconds=10),
        )
        self.title_has_been_checked = True
        return is_valid


@activity.defn
async def check_title_validity(title: str) -> bool:
    return True


async def main():
    client = await cl.Client.connect("localhost:7233")
    handle = await client.start_workflow(
        Workflow.get_greeting,
        MyWorkflowInput(name="John"),
        id="wid",
        task_queue="tq",
        id_reuse_policy=common.WorkflowIDReusePolicy.TERMINATE_IF_RUNNING,
    )
    update_handle = await handle.start_update(
        Workflow.check_title_validity, wait_for_stage=WorkflowUpdateStage.ACCEPTED
    )
    print(await update_handle.result())
    print(await handle.result())


if __name__ == "__main__":
    asyncio.run(main())
