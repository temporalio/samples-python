import asyncio
import os
from importlib import import_module
from pathlib import Path
from typing import Callable, Type

import xray
from opentelemetry import trace
from temporalio.worker import UnsandboxedWorkflowRunner, Worker

from dan.constants import NAMESPACE, TASK_QUEUE
from dan.utils import connect


def get_last_edited_workflow_module():
    root_dir = Path(__file__).parent.parent
    workflow_files = []
    for f in root_dir.glob("*.py"):
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
activities: list[Callable] = getattr(latest_module, "activities", [])
workflows: list[Type] = getattr(latest_module, "workflows", [latest_module.Workflow])

interrupt_event = asyncio.Event()


async def main(workflows: list[Type], activities: list[Callable]):
    print(NAMESPACE, latest_module.__name__)
    if os.getenv("TRACING"):
        print("🩻")
        trace.set_tracer_provider(xray.create_tracer_provider("Lang"))
    client = await connect()
    async with Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=workflows,
        activities=activities,
        workflow_runner=UnsandboxedWorkflowRunner(),
    ):
        await interrupt_event.wait()


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(main(workflows, activities))
    except KeyboardInterrupt:
        interrupt_event.set()
        loop.run_until_complete(loop.shutdown_asyncgens())
