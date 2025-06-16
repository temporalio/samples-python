"""
Changes the log level of workflow task failures from WARN to ERROR.
"""

import asyncio
import logging
import sys

from temporalio import workflow
from temporalio.client import Client
from temporalio.worker import Worker

# --- Begin logging set‑up ----------------------------------------------------------
logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)


class CustomLogFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if (
            record.msg.startswith("Failed activation on workflow")
            and record.levelno < logging.ERROR
        ):
            record.levelno = logging.ERROR
            record.levelname = logging.getLevelName(logging.ERROR)
        return True


logging.getLogger("temporalio.worker._workflow_instance").addFilter(CustomLogFilter())
# --- End logging set‑up ----------------------------------------------------------


LOG_MESSAGE = "This error is an experiment to check the log level"


@workflow.defn
class GreetingWorkflow:
    @workflow.run
    async def run(self):
        raise RuntimeError(LOG_MESSAGE)


async def main():
    client = await Client.connect("localhost:7233")
    async with Worker(
        client,
        task_queue="hello-task-queue",
        workflows=[GreetingWorkflow],
    ):
        await client.execute_workflow(
            GreetingWorkflow.run,
            id="hello-workflow-id",
            task_queue="hello-task-queue",
        )


if __name__ == "__main__":
    asyncio.run(main())
