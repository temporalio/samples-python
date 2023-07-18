import argparse
import asyncio

from temporalio.client import Client
from temporalio.worker import Worker

from patching.activities import post_patch_activity, pre_patch_activity

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
        from patching.workflow_1_initial import MyWorkflow
    elif args.workflow == "patched":
        from patching.workflow_2_patched import MyWorkflow  # type: ignore
    elif args.workflow == "patch-deprecated":
        from patching.workflow_3_patch_deprecated import MyWorkflow  # type: ignore
    elif args.workflow == "patch-complete":
        from patching.workflow_4_patch_complete import MyWorkflow  # type: ignore
    else:
        raise RuntimeError("Unrecognized workflow")

    # Connect client
    client = await Client.connect("localhost:7233")

    # Run a worker for the workflow
    async with Worker(
        client,
        task_queue="patching-task-queue",
        workflows=[MyWorkflow],
        activities=[pre_patch_activity, post_patch_activity],
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
