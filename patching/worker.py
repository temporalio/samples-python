import argparse
import asyncio

from temporalio.client import Client
from temporalio.worker import Worker

interrupt_event = asyncio.Event()


async def main():
    # Import which workflow based on CLI arg
    parser = argparse.ArgumentParser(description="Run worker")
    parser.add_argument(
        "--workflow",
        help="Which workflow. Can be 'initial', 'patched', 'patch-deprecated', or 'patch-complete'",
        required=True,
    )
    args = parser.parse_args()
    if args.workflow == "initial":
        from workflow_1_initial import MyWorkflow
    elif args.workflow == "patched":
        from workflow_2_patched import MyWorkflow
    elif args.workflow == "patch-deprecated":
        from workflow_3_patch_deprecated import MyWorkflow
    elif args.workflow == "patch-complete":
        from workflow_4_patch_complete import MyWorkflow
    else:
        raise RuntimeError("Unrecognized workflow")

    # Connect client
    client = await Client.connect("localhost:7233")

    # Run a worker for the workflow
    async with Worker(
        client,
        task_queue="patching-task-queue",
        workflows=[MyWorkflow],
    ):
        # Wait until interrupted
        print("Worker started")
        await interrupt_event.wait()
        print("Shutting down")


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        interrupt_event.set()
        loop.run_until_complete(loop.shutdown_asyncgens())
