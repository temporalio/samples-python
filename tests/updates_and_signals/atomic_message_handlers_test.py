import uuid

from temporalio import common, workflow
from temporalio.client import Client
from temporalio.worker import Worker

from updates_and_signals.atomic_message_handlers.activities import (
    allocate_nodes_to_job,
    deallocate_nodes_for_job,
    find_bad_nodes,
)
from updates_and_signals.atomic_message_handlers.starter import do_cluster_lifecycle
from updates_and_signals.atomic_message_handlers.workflow import (
    ClusterManagerInput,
    ClusterManagerWorkflow,
)


async def test_atomic_message_handlers(client: Client):
    task_queue = f"tq-{uuid.uuid4()}"
    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[ClusterManagerWorkflow],
        activities=[allocate_nodes_to_job, deallocate_nodes_for_job, find_bad_nodes],
    ):
        cluster_manager_handle = await client.start_workflow(
            ClusterManagerWorkflow.run,
            ClusterManagerInput(),
            id=f"ClusterManagerWorkflow-{uuid.uuid4()}",
            task_queue=task_queue,
            start_signal="start_cluster",
        )
        await do_cluster_lifecycle(cluster_manager_handle, delay_seconds=1)
        result = await cluster_manager_handle.result()
        assert result.max_assigned_nodes == 12
        assert result.num_assigned_nodes == 0
