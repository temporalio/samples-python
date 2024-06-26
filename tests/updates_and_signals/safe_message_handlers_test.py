import uuid

from temporalio import common, workflow
from temporalio.client import Client, WorkflowUpdateFailedError
from temporalio.exceptions import ApplicationError
from temporalio.worker import Worker

from updates_and_signals.safe_message_handlers.activities import (
    allocate_nodes_to_job,
    deallocate_nodes_for_job,
    find_bad_nodes,
)
from updates_and_signals.safe_message_handlers.starter import do_cluster_lifecycle
from updates_and_signals.safe_message_handlers.workflow import (
    ClusterManagerAllocateNNodesToJobInput,
    ClusterManagerInput,
    ClusterManagerWorkflow,
)


async def test_safe_message_handlers(client: Client):
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
        )
        await do_cluster_lifecycle(cluster_manager_handle, delay_seconds=1)
        result = await cluster_manager_handle.result()
        assert result.max_assigned_nodes == 12
        assert result.num_currently_assigned_nodes == 0


async def test_update_idempotency(client: Client):
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
        )

        await cluster_manager_handle.signal(ClusterManagerWorkflow.start_cluster)

        nodes_1 = await cluster_manager_handle.execute_update(
            ClusterManagerWorkflow.allocate_n_nodes_to_job,
            ClusterManagerAllocateNNodesToJobInput(num_nodes=5, job_name=f"jobby-job"),
        )
        # simulate that in calling it twice, the operation is idempotent
        nodes_2 = await cluster_manager_handle.execute_update(
            ClusterManagerWorkflow.allocate_n_nodes_to_job,
            ClusterManagerAllocateNNodesToJobInput(num_nodes=5, job_name=f"jobby-job"),
        )
        # the second call should not allocate more nodes (it may return fewer if the health check finds bad nodes
        # in between the two signals.)
        assert nodes_1 >= nodes_2


async def test_update_failure(client: Client):
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
        )

        await cluster_manager_handle.signal(ClusterManagerWorkflow.start_cluster)

        await cluster_manager_handle.execute_update(
            ClusterManagerWorkflow.allocate_n_nodes_to_job,
            ClusterManagerAllocateNNodesToJobInput(num_nodes=24, job_name=f"big-task"),
        )
        try:
            # Try to allocate too many nodes
            await cluster_manager_handle.execute_update(
                ClusterManagerWorkflow.allocate_n_nodes_to_job,
                ClusterManagerAllocateNNodesToJobInput(
                    num_nodes=3, job_name=f"little-task"
                ),
            )
        except WorkflowUpdateFailedError as e:
            assert isinstance(e.cause, ApplicationError)
            assert e.cause.message == "Cannot allocate 3 nodes; have only 1 available"
        finally:
            await cluster_manager_handle.signal(ClusterManagerWorkflow.shutdown_cluster)
            result = await cluster_manager_handle.result()
            assert result.num_currently_assigned_nodes + result.num_bad_nodes == 24
