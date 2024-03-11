import asyncio
import socket
from datetime import datetime, timedelta
from typing import Iterator, List
from uuid import uuid4

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

WORKFLOW_ID = uuid4().hex
TASK_QUEUE = __file__

N_UPDATES = 1
REPLAY = True


@activity.defn
async def my_activity(arg: int) -> str:
    return f"activity-result-{arg}"


@workflow.defn(sandboxed=False)
class WorkflowWithUpdateHandler:
    def __init__(self) -> None:
        self.update_results = []

    @workflow.update
    async def my_update(self, arg: int):
        r = await workflow.execute_activity(
            my_activity, arg, start_to_close_timeout=timedelta(seconds=10)
        )
        self.update_results.append(r)
        return self.update_results

    @workflow.run
    async def run(self):
        await workflow.wait_condition(lambda: len(self.update_results) == N_UPDATES)
        return {"update_results": self.update_results}


async def app(client: Client):
    handle = await client.start_workflow(
        WorkflowWithUpdateHandler.run,
        id=WORKFLOW_ID,
        task_queue=TASK_QUEUE,
        id_reuse_policy=temporalio.common.WorkflowIDReusePolicy.TERMINATE_IF_RUNNING,
    )

    log(
        f"sent start workflow request http://{server()}/namespaces/default/workflows/{WORKFLOW_ID}"
    )

    for i in range(N_UPDATES):
        if True or input("execute update?") in ["y", ""]:
            log("sending update...")
            result = await handle.execute_update(
                WorkflowWithUpdateHandler.my_update, arg=i
            )
            log(f"received update result: {result}")

    if True or input("reset?") in ["y", ""]:
        history = [e async for e in handle.fetch_history_events()]
        reset_to = next_event(
            history,
            temporalio.api.enums.v1.EventType.EVENT_TYPE_WORKFLOW_TASK_COMPLETED,
        )

        log(f"sending reset to event {reset_to.event_id}...")
        run_id = get_first_execution_run_id(history)
        new_run_id = await reset_workflow(run_id, reset_to, client)
        log(
            f"did reset: http://localhost:8080/namespaces/default/workflows/{WORKFLOW_ID}/{new_run_id}"
        )

        new_handle = client.get_workflow_handle(WORKFLOW_ID, run_id=new_run_id)

        history = [e async for e in new_handle.fetch_history_events()]

        log("new history")
        for e in history:
            log(f"{e.event_id} {e.event_type}")

        wf_result = await new_handle.result()
        print(f"reset wf result: {wf_result}")
        log(f"reset wf result: {wf_result}")
    else:
        wf_result = await handle.result()
        print(f"wf result: {wf_result}")
        log(f"wf result: {wf_result}")


async def reset_workflow(
    run_id: str,
    event: temporalio.api.history.v1.HistoryEvent,
    client: Client,
) -> RunId:
    resp = await client.workflow_service.reset_workflow_execution(
        temporalio.api.workflowservice.v1.ResetWorkflowExecutionRequest(
            namespace="default",
            workflow_execution=temporalio.api.common.v1.WorkflowExecution(
                workflow_id=WORKFLOW_ID,
                run_id=run_id,
            ),
            reason="Reset to test update reapply",
            request_id="1",
            reset_reapply_type=temporalio.api.enums.v1.ResetReapplyType.RESET_REAPPLY_TYPE_UNSPECIFIED,  # TODO
            workflow_task_finish_event_id=event.event_id,
        )
    )
    assert resp.run_id
    return resp.run_id


def next_event(
    history: List[temporalio.api.history.v1.HistoryEvent],
    event_type: temporalio.api.enums.v1.EventType.ValueType,
) -> temporalio.api.history.v1.HistoryEvent:
    return next(e for e in history if e.event_type == event_type)


def get_first_execution_run_id(
    history: List[temporalio.api.history.v1.HistoryEvent],
) -> str:
    # TODO: correct way to obtain run_id
    wf_started_event = next_event(
        history, temporalio.api.enums.v1.EventType.EVENT_TYPE_WORKFLOW_EXECUTION_STARTED
    )
    run_id = (
        wf_started_event.workflow_execution_started_event_attributes.first_execution_run_id
    )
    assert run_id
    return run_id


async def main():
    client = await Client.connect("localhost:7233")
    async with Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[WorkflowWithUpdateHandler],
        activities=[my_activity],
        sticky_queue_schedule_to_start_timeout=timedelta(hours=1),
        max_cached_workflows=0 if REPLAY else 100,
    ):
        await app(client)


def only(it: Iterator):
    t = next(it)
    assert (t2 := next(it, it)) == it, f"iterator had multiple items: [{t}, {t2}]"
    return t


def is_listening(addr: str) -> bool:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    h, p = addr.split(":")
    try:
        s.connect((h, int(p)))
        return True
    except socket.error:
        return False
    finally:
        s.close()


def server() -> str:
    return only(
        filter(
            is_listening,
            ["localhost:8080", "localhost:8081", "localhost:8233"],
        )
    )


def log(s: str):
    log_to_file(s, "client", "red")


def log_to_file(msg: str, prefix: str, color: str):
    with open("/tmp/log", "a") as f:
        time = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        print(
            f"\n\n======================\n[{color}]{time} : {prefix} : {msg}[/{color}]\n\n",
            file=f,
        )


if __name__ == "__main__":
    asyncio.run(main())
