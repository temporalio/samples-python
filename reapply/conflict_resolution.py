import asyncio
import sys
from datetime import timedelta

import temporalio.api.common.v1
import temporalio.api.enums.v1
import temporalio.api.history.v1
import temporalio.api.workflowservice.v1
import temporalio.common
from temporalio import activity, workflow
from temporalio.client import Client
from temporalio.worker import Worker

try:
    from rich import print
except ImportError:
    pass

RunId = str

NAMESPACE = "ns1"
WORKFLOW_ID = "my-workflow-id"
TASK_QUEUE = "my-task-queue"
N_SIGNALS = 1
N_UPDATES = 0
REPLAY = False


@activity.defn
async def my_activity(arg: str) -> str:
    return f"activity-result-{arg}"


@workflow.defn(name="my-workflow", sandboxed=False)
class MyWorkflow:
    def __init__(self) -> None:
        self.done = False
        self.signal_results = []
        self.update_results = []

    @workflow.signal(name="my-signal")
    async def my_signal(self, arg: str):
        if arg == "done":
            self.done = True
        else:
            self.signal_results.append(arg)

    @workflow.update(name="my-update")
    async def my_update(self, arg: str):
        r = await workflow.execute_activity(
            my_activity, arg, start_to_close_timeout=timedelta(seconds=10)
        )
        self.update_results.append(r)
        return self.update_results

    @workflow.run
    async def run(self):
        await workflow.wait_condition(lambda: self.done)
        return {
            "signal_results": self.signal_results,
            "update_results": self.update_results,
        }


async def execute_workflow(client: Client):
    handle = await client.start_workflow(
        MyWorkflow.run,
        id=WORKFLOW_ID,
        task_queue=TASK_QUEUE,
        id_reuse_policy=temporalio.common.WorkflowIDReusePolicy.TERMINATE_IF_RUNNING,
    )

    print(
        f"started workflow: http://localhost:XXXX/namespaces/default/workflows/{WORKFLOW_ID}"
    )
    wf_result = await handle.result()
    print(f"wf result: {wf_result}")


async def main(address: str):
    client = await Client.connect(address, namespace=NAMESPACE)
    async with Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[MyWorkflow],
        activities=[my_activity],
        sticky_queue_schedule_to_start_timeout=timedelta(hours=1),
        max_cached_workflows=0 if REPLAY else 100,
    ):
        await asyncio.sleep(0xFFFFFF)


if __name__ == "__main__":
    [address] = sys.argv[1:]
    asyncio.run(main(address))
