import argparse
import asyncio
import concurrent.futures
import dataclasses
import multiprocessing
import traceback
from typing import Literal

from temporalio.client import Client
from temporalio.envconfig import ClientConfig
from temporalio.runtime import Runtime, TelemetryConfig
from temporalio.worker import PollerBehaviorSimpleMaximum, Worker
from temporalio.worker.workflow_sandbox import (
    SandboxedWorkflowRunner,
    SandboxRestrictions,
)

from workflow_task_multiprocessing import ACTIVITY_TASK_QUEUE, WORKFLOW_TASK_QUEUE
from workflow_task_multiprocessing.activities import echo_pid_activity
from workflow_task_multiprocessing.workflows import ParallelizedWorkflow

# Immediately prevent the default Runtime from being created to ensure
# each process creates it's own
Runtime.prevent_default()


class Args(argparse.Namespace):
    num_workflow_workers: int
    num_activity_workers: int

    @property
    def total_workers(self) -> int:
        return self.num_activity_workers + self.num_workflow_workers


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-w", "--num-workflow-workers", type=int, default=2)
    parser.add_argument("-a", "--num-activity-workers", type=int, default=1)
    args = parser.parse_args(namespace=Args())
    print(
        f"starting {args.num_workflow_workers} workflow worker(s) and {args.num_activity_workers} activity worker(s)"
    )

    # This sample prefers fork to avoid re-importing modules
    # and decrease startup time. Fork is not available on all
    # operating systems, so we fallback to 'spawn' when not available
    try:
        mp_ctx = multiprocessing.get_context("fork")
    except ValueError:
        mp_ctx = multiprocessing.get_context("spawn")  # type: ignore

    with concurrent.futures.ProcessPoolExecutor(
        args.total_workers, mp_context=mp_ctx
    ) as executor:
        # Start workflow workers by submitting them to the
        # ProcessPoolExecutor
        worker_futures = [
            executor.submit(worker_entry, "workflow", i)
            for i in range(args.num_workflow_workers)
        ]

        # In this sample, we start activity workers as separate processes in the
        # same way we do workflow workers. In production, activity workers
        # are often deployed separately from workflow workers to account for
        # differing scaling characteristics.
        worker_futures.extend(
            [
                executor.submit(worker_entry, "activity", i)
                for i in range(args.num_activity_workers)
            ]
        )

        try:
            print("waiting for keyboard interrupt or for all workers to exit")
            for worker in concurrent.futures.as_completed(worker_futures):
                print("ERROR: worker exited unexpectedly")
                if worker.exception():
                    traceback.print_exception(worker.exception())
        except KeyboardInterrupt:
            pass


def worker_entry(worker_type: Literal["workflow", "activity"], id: int):
    Runtime.set_default(Runtime(telemetry=TelemetryConfig()))

    async def run_worker():
        config = ClientConfig.load_client_connect_config()
        config.setdefault("target_host", "localhost:7233")
        client = await Client.connect(**config)

        if worker_type == "workflow":
            worker = workflow_worker(client)
        else:
            worker = activity_worker(client)

        try:
            print(f"{worker_type}-worker:{id} starting")
            await asyncio.shield(worker.run())
        except asyncio.CancelledError:
            print(f"{worker_type}-worker:{id} shutting down")
            await worker.shutdown()

    asyncio.run(run_worker())


def workflow_worker(client: Client) -> Worker:
    """
    Create a workflow worker that is configured to leverage being run
    as many child processes.
    """
    return Worker(
        client,
        task_queue=WORKFLOW_TASK_QUEUE,
        workflows=[ParallelizedWorkflow],
        # Workflow tasks are CPU bound, but generally execute quickly.
        # Because we're leveraging multiprocessing to achieve parallelism,
        # we want each workflow worker to be confirgured for small workflow
        # task processing.
        max_concurrent_workflow_tasks=2,
        workflow_task_poller_behavior=PollerBehaviorSimpleMaximum(2),
        # Allow workflows to access the os module to access the pid
        workflow_runner=SandboxedWorkflowRunner(
            restrictions=dataclasses.replace(
                SandboxRestrictions.default,
                invalid_module_members=SandboxRestrictions.invalid_module_members_default.with_child_unrestricted(
                    "os"
                ),
            )
        ),
    )


def activity_worker(client: Client) -> Worker:
    """
    Create a basic activity worker
    """
    return Worker(
        client,
        task_queue=ACTIVITY_TASK_QUEUE,
        activities=[echo_pid_activity],
    )


if __name__ == "__main__":
    main()
