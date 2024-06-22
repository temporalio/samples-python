import asyncio
import logging
import uuid
from typing import Optional

from temporalio import client, common
from temporalio.client import Client, WorkflowHandle

from updates_and_signals.atomic_message_handlers.workflow import ClusterManagerWorkflow


async def do_cluster_lifecycle(wf: WorkflowHandle, delay_seconds: Optional[int] = None):
    allocation_updates = []
    for i in range(6):
        allocation_updates.append(
            wf.execute_update(
                ClusterManagerWorkflow.allocate_n_nodes_to_job, args=[f"task-{i}", 2]
            )
        )
    await asyncio.gather(*allocation_updates)

    if delay_seconds:
        await asyncio.sleep(delay_seconds)

    deletion_updates = []
    for i in range(6):
        deletion_updates.append(
            wf.execute_update(ClusterManagerWorkflow.delete_job, f"task-{i}")
        )
    await asyncio.gather(*deletion_updates)

    await wf.signal(ClusterManagerWorkflow.shutdown_cluster)


async def main():
    # Connect to Temporal
    client = await Client.connect("localhost:7233")

    cluster_manager_handle = await client.start_workflow(
        ClusterManagerWorkflow.run,
        args=[None, 150],  # max_history_length to conveniently test continue-as-new
        id=f"ClusterManagerWorkflow-{uuid.uuid4()}",
        task_queue="atomic-message-handlers-task-queue",
        id_reuse_policy=common.WorkflowIDReusePolicy.TERMINATE_IF_RUNNING,
        start_signal="start_cluster",
    )
    await do_cluster_lifecycle(cluster_manager_handle, delay_seconds=1)
    result = await cluster_manager_handle.result()
    print(
        f"Cluster shut down successfully.  It peaked at {result.max_assigned_nodes} assigned nodes ."
        f" It had {result.num_assigned_nodes} nodes assigned at the end."
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    asyncio.run(main())
