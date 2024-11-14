import argparse
import asyncio
import logging
import uuid
from typing import Optional

from temporalio import common
from temporalio.client import Client, WorkflowHandle

from message_passing.safe_message_handlers.workflow import (
    ClusterManagerAssignNodesToJobInput,
    ClusterManagerDeleteJobInput,
    ClusterManagerInput,
    ClusterManagerWorkflow,
)


async def do_cluster_lifecycle(wf: WorkflowHandle, delay_seconds: Optional[int] = None):

    await wf.signal(ClusterManagerWorkflow.start_cluster)

    print("Assigning jobs to nodes...")
    allocation_updates = []
    for i in range(6):
        allocation_updates.append(
            wf.execute_update(
                ClusterManagerWorkflow.assign_nodes_to_job,
                ClusterManagerAssignNodesToJobInput(
                    total_num_nodes=2, job_name=f"task-{i}"
                ),
            )
        )
    await asyncio.gather(*allocation_updates)

    print(f"Sleeping for {delay_seconds} second(s)")
    if delay_seconds:
        await asyncio.sleep(delay_seconds)

    print("Deleting jobs...")
    deletion_updates = []
    for i in range(6):
        deletion_updates.append(
            wf.execute_update(
                ClusterManagerWorkflow.delete_job,
                ClusterManagerDeleteJobInput(job_name=f"task-{i}"),
            )
        )
    await asyncio.gather(*deletion_updates)

    await wf.signal(ClusterManagerWorkflow.shutdown_cluster)


async def main(should_test_continue_as_new: bool):
    # Connect to Temporal
    client = await Client.connect("localhost:7233")

    print("Starting cluster")
    cluster_manager_handle = await client.start_workflow(
        ClusterManagerWorkflow.run,
        ClusterManagerInput(test_continue_as_new=should_test_continue_as_new),
        id=f"ClusterManagerWorkflow-{uuid.uuid4()}",
        task_queue="safe-message-handlers-task-queue",
        id_reuse_policy=common.WorkflowIDReusePolicy.TERMINATE_IF_RUNNING,
    )
    delay_seconds = 10 if should_test_continue_as_new else 1
    await do_cluster_lifecycle(cluster_manager_handle, delay_seconds=delay_seconds)
    result = await cluster_manager_handle.result()
    print(
        f"Cluster shut down successfully."
        f" It had {result.num_currently_assigned_nodes} nodes assigned at the end."
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description="Atomic message handlers")
    parser.add_argument(
        "--test-continue-as-new",
        help="Make the ClusterManagerWorkflow continue as new before shutting down",
        action="store_true",
        default=False,
    )
    args = parser.parse_args()
    asyncio.run(main(args.test_continue_as_new))
