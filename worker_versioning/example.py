import asyncio
import uuid

from temporalio.client import (Client, BuildIdOpAddNewDefault, BuildIdOpAddNewCompatible)
from temporalio.worker import Worker

from worker_versioning.activities import greet, super_greet
from worker_versioning.workflow_v1 import MyWorkflow as MyWorkflowV1
from worker_versioning.workflow_v1_1 import MyWorkflow as MyWorkflowV1_1
from worker_versioning.workflow_v2 import MyWorkflow as MyWorkflowV2


async def main():
    client = await Client.connect("localhost:7233")
    task_queue = f"worker-versioning-{uuid.uuid4()}"

    # Start a 1.0 worker
    async with Worker(
            client,
            task_queue=task_queue,
            workflows=[MyWorkflowV1],
            activities=[greet, super_greet],
    ):
        # Add 1.0 as the default version for the queue
        await client.update_worker_build_id_compatibility(task_queue, BuildIdOpAddNewDefault("1.0"))

        # Start a workflow which will run on the 1.0 worker
        handle = await client.start_workflow(MyWorkflowV1.run, task_queue=task_queue,
                                             id=f"worker-versioning-v1-{uuid.uuid4()}")
        # Signal the workflow to proceed
        await handle.signal(MyWorkflowV1.signal, "go")

        # Give a chance for the worker to process the signal
        # TODO Better?
        await asyncio.sleep(1)

    # Add 1.1 as the default version for the queue, compatible with 1.0
    await client.update_worker_build_id_compatibility(task_queue, BuildIdOpAddNewCompatible("1.1", "1.0"))

    # Stop the old worker, and start a 1.1 worker. We do this to speed along the example, since the
    # 1.0 worker may continue to process tasks briefly after we make 1.1 the new default.
    async with Worker(
            client,
            task_queue=task_queue,
            workflows=[MyWorkflowV1_1],
            activities=[greet, super_greet],
    ):
        # Continue driving the workflow. Take note that the new version of the workflow run by the 1.1
        # worker is the one that takes over! You might see a workflow task timeout, if the 1.0 worker is
        # processing a task as the version update happens. That's normal.
        await handle.signal(MyWorkflowV1.signal, "go")

        # Add a new *incompatible* version to the task queue, which will become the new overall default for the queue.
        await client.update_worker_build_id_compatibility(task_queue, BuildIdOpAddNewDefault("2.0"))

        # Start a 2.0 worker
        async with Worker(
                client,
                task_queue=task_queue,
                workflows=[MyWorkflowV2],
                activities=[greet, super_greet],
        ):
            # Start a new workflow. Note that it will run on the new 2.0 version, without the client invocation changing
            # at all! Note here we can use `MyWorkflowV1.run` because the signature of the workflow has not changed.
            handle2 = await client.start_workflow(MyWorkflowV1.run, task_queue=task_queue,
                                                  id=f"worker-versioning-v2-{uuid.uuid4()}")

            # Drive both workflows once more before concluding them. The first workflow will continue running on the 1.1
            # worker.
            await handle.signal(MyWorkflowV1.signal, "go")
            await handle2.signal(MyWorkflowV1.signal, "go")
            await handle.signal(MyWorkflowV1.signal, "finish")
            await handle2.signal(MyWorkflowV1.signal, "finish")

            # Wait for both workflows to complete
            await handle.result()
            await handle2.result()

            # Lastly we'll demonstrate how you can use the gRPC api to determine if certain build IDs are ready to be
            # retired. There's more information in the documentation, but here's a quick example that shows us how to
            # tell when the 1.0 worker can be retired:

            # There is a 5 minute buffer before we will consider IDs no longer reachable by new workflows, to
            # account for replication in multi-cluster setups. Uncomment the following line to wait long enough to see
            # the 1.0 worker become unreachable.
            # await asyncio.sleep(60 * 5)
            reachability = await client.get_worker_task_reachability(
                build_ids=["2.0", "1.0", "1.1"]
            )

            if not reachability.build_id_reachability["1.0"].task_queue_reachability[task_queue]:
                print("1.0 is ready to be retired!")


if __name__ == "__main__":
    asyncio.run(main())
