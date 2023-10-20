# Init gevent
from gevent import monkey

monkey.patch_all()

import asyncio
import logging

from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from gevent_async import activity, workflow
from gevent_async.executor import GeventExecutor

# This basically combines ../worker.py and ../starter.py for use by CI to
# confirm this works in all environments


def main():
    logging.basicConfig(level=logging.INFO)
    with GeventExecutor(max_workers=1) as executor:
        executor.submit(asyncio.run, async_main()).result()


async def async_main():
    logging.info("Starting local server")
    async with await WorkflowEnvironment.start_local() as env:
        logging.info("Starting worker")
        with GeventExecutor(max_workers=200) as executor:
            async with Worker(
                env.client,
                task_queue="gevent_async-task-queue",
                workflows=[workflow.GreetingWorkflow],
                activities=[
                    activity.compose_greeting_async,
                    activity.compose_greeting_sync,
                ],
                activity_executor=executor,
                workflow_task_executor=executor,
                max_concurrent_activities=100,
                max_concurrent_workflow_tasks=100,
            ):
                logging.info("Running workflow")
                result = await env.client.execute_workflow(
                    workflow.GreetingWorkflow.run,
                    "Temporal",
                    id="gevent_async-workflow-id",
                    task_queue="gevent_async-task-queue",
                )
                if result != "Hello, Temporal!":
                    raise RuntimeError(f"Unexpected result: {result}")
                logging.info(f"Workflow complete, result: {result}")


if __name__ == "__main__":
    main()
