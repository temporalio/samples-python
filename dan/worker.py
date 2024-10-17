import asyncio
import os
from importlib import import_module
from pathlib import Path

from temporalio.worker import UnsandboxedWorkflowRunner, Worker

import dan.utils
from dan.constants import NAMESPACE, TASK_QUEUE


def get_last_edited_workflow_module():
    dan_dir = Path(__file__).parent
    workflow_files = []
    for f in dan_dir.glob("*.py"):
        if f.is_file():
            if f.stem == "worker":
                continue
            try:
                module = import_module(f"dan.{f.stem}")
            except NameError:
                continue
            if hasattr(module, "Workflow"):
                workflow_files.append(f)
    latest_file = max(workflow_files, key=os.path.getmtime)
    return import_module(f"dan.{latest_file.stem}")


latest_module = get_last_edited_workflow_module()
Workflow = latest_module.Workflow
activities = getattr(latest_module, "activities", [])

interrupt_event = asyncio.Event()


async def main():
    print(NAMESPACE, Workflow.__module__)
    client = await dan.utils.connect("Lang")
    async with Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[Workflow],
        activities=activities,
        workflow_runner=UnsandboxedWorkflowRunner(),
    ):
        await interrupt_event.wait()


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        interrupt_event.set()
        loop.run_until_complete(loop.shutdown_asyncgens())
