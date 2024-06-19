import uuid

from temporalio import workflow, common
from temporalio.client import Client
from temporalio.worker import Worker
from update_and_signal_handlers.atomic_message_handlers import ClusterManager, allocate_nodes_to_job, deallocate_nodes_for_job, do_cluster_lifecycle, find_bad_nodes


async def test_atomic_message_handlers(client: Client):
    async with Worker(
        client,
        task_queue="tq",
        workflows=[ClusterManager],
        activities=[allocate_nodes_to_job, deallocate_nodes_for_job, find_bad_nodes],
    ):
        cluster_manager_handle = await client.start_workflow(
            ClusterManager.run,
            id=f"ClusterManager-{uuid.uuid4()}",
            task_queue="tq",
            id_reuse_policy=common.WorkflowIDReusePolicy.TERMINATE_IF_RUNNING,
            start_signal='start_cluster',

        )
        await do_cluster_lifecycle(cluster_manager_handle)
        max_assigned_nodes = await cluster_manager_handle.result()
        assert max_assigned_nodes == 12
