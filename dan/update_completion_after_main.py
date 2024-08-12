import asyncio
import uuid

from temporalio import workflow
from temporalio.client import Client
from temporalio.worker import Worker
from utils import update_has_been_admitted

wid = __file__
tq = "tq"


@workflow.defn
class UpdateCompletionAfterWorkflowReturn:
    def __init__(self) -> None:
        self.workflow_returned = False

    @workflow.run
    async def run(self) -> str:
        self.workflow_returned = True
        return "workflow-result"

    @workflow.update
    async def my_update(self) -> str:
        await workflow.wait_condition(lambda: self.workflow_returned)
        return "update-result"


async def main():
    client = await Client.connect("localhost:7233")

    update_id = "my-update"
    task_queue = "tq"
    wf_handle = await client.start_workflow(
        UpdateCompletionAfterWorkflowReturn.run,
        id=f"wf-{uuid.uuid4()}",
        task_queue=task_queue,
    )
    update_result_task = asyncio.create_task(
        wf_handle.execute_update(
            UpdateCompletionAfterWorkflowReturn.my_update,
            id=update_id,
        )
    )
    await update_has_been_admitted(client, wf_handle.id, update_id)

    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[UpdateCompletionAfterWorkflowReturn],
    ):
        assert await wf_handle.result() == "workflow-result"
        assert await update_result_task == "update-result"


if __name__ == "__main__":
    asyncio.run(main())
