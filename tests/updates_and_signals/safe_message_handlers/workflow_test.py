import asyncio
import uuid

import pytest
from temporalio.client import Client, WorkflowUpdateFailedError
from temporalio.exceptions import ApplicationError
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from message_passing.safe_message_handlers.activities import (
    assign_nodes_to_job,
    find_bad_nodes,
    unassign_nodes_for_job,
)
from message_passing.safe_message_handlers.workflow import (
    ClusterManagerAssignNodesToJobInput,
    ClusterManagerDeleteJobInput,
    ClusterManagerInput,
    ClusterManagerWorkflow,
)


async def test_safe_message_handlers(client: Client, env: WorkflowEnvironment):
    if env.supports_time_skipping:
        pytest.skip(
            "Java test server: https://github.com/temporalio/sdk-java/issues/1903"
        )
    task_queue = f"tq-{uuid.uuid4()}"
    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[ClusterManagerWorkflow],
        activities=[assign_nodes_to_job, unassign_nodes_for_job, find_bad_nodes],
    ):
        cluster_manager_handle = await client.start_workflow(
            ClusterManagerWorkflow.run,
            ClusterManagerInput(),
            id=f"ClusterManagerWorkflow-{uuid.uuid4()}",
            task_queue=task_queue,
        )
        await cluster_manager_handle.signal(ClusterManagerWorkflow.start_cluster)

        allocation_updates = []
        for i in range(6):
            allocation_updates.append(
                cluster_manager_handle.execute_update(
                    ClusterManagerWorkflow.assign_nodes_to_job,
                    ClusterManagerAssignNodesToJobInput(
                        total_num_nodes=2, job_name=f"task-{i}"
                    ),
                )
            )
        results = await asyncio.gather(*allocation_updates)
        for result in results:
            assert len(result.nodes_assigned) == 2

        await asyncio.sleep(1)

        deletion_updates = []
        for i in range(6):
            deletion_updates.append(
                cluster_manager_handle.execute_update(
                    ClusterManagerWorkflow.delete_job,
                    ClusterManagerDeleteJobInput(job_name=f"task-{i}"),
                )
            )
        await asyncio.gather(*deletion_updates)

        await cluster_manager_handle.signal(ClusterManagerWorkflow.shutdown_cluster)

        result = await cluster_manager_handle.result()
        assert result.num_currently_assigned_nodes == 0


async def test_update_idempotency(client: Client, env: WorkflowEnvironment):
    if env.supports_time_skipping:
        pytest.skip(
            "Java test server: https://github.com/temporalio/sdk-java/issues/1903"
        )
    task_queue = f"tq-{uuid.uuid4()}"
    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[ClusterManagerWorkflow],
        activities=[assign_nodes_to_job, unassign_nodes_for_job, find_bad_nodes],
    ):
        cluster_manager_handle = await client.start_workflow(
            ClusterManagerWorkflow.run,
            ClusterManagerInput(),
            id=f"ClusterManagerWorkflow-{uuid.uuid4()}",
            task_queue=task_queue,
        )

        await cluster_manager_handle.signal(ClusterManagerWorkflow.start_cluster)

        result_1 = await cluster_manager_handle.execute_update(
            ClusterManagerWorkflow.assign_nodes_to_job,
            ClusterManagerAssignNodesToJobInput(
                total_num_nodes=5, job_name="jobby-job"
            ),
        )
        # simulate that in calling it twice, the operation is idempotent
        result_2 = await cluster_manager_handle.execute_update(
            ClusterManagerWorkflow.assign_nodes_to_job,
            ClusterManagerAssignNodesToJobInput(
                total_num_nodes=5, job_name="jobby-job"
            ),
        )
        # the second call should not assign more nodes (it may return fewer if the health check finds bad nodes
        # in between the two signals.)
        assert result_1.nodes_assigned >= result_2.nodes_assigned


async def test_update_failure(client: Client, env: WorkflowEnvironment):
    if env.supports_time_skipping:
        pytest.skip(
            "Java test server: https://github.com/temporalio/sdk-java/issues/1903"
        )
    task_queue = f"tq-{uuid.uuid4()}"
    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[ClusterManagerWorkflow],
        activities=[assign_nodes_to_job, unassign_nodes_for_job, find_bad_nodes],
    ):
        cluster_manager_handle = await client.start_workflow(
            ClusterManagerWorkflow.run,
            ClusterManagerInput(),
            id=f"ClusterManagerWorkflow-{uuid.uuid4()}",
            task_queue=task_queue,
        )

        await cluster_manager_handle.signal(ClusterManagerWorkflow.start_cluster)

        await cluster_manager_handle.execute_update(
            ClusterManagerWorkflow.assign_nodes_to_job,
            ClusterManagerAssignNodesToJobInput(
                total_num_nodes=24, job_name="big-task"
            ),
        )
        try:
            # Try to assign too many nodes
            await cluster_manager_handle.execute_update(
                ClusterManagerWorkflow.assign_nodes_to_job,
                ClusterManagerAssignNodesToJobInput(
                    total_num_nodes=3, job_name="little-task"
                ),
            )
        except WorkflowUpdateFailedError as e:
            assert isinstance(e.cause, ApplicationError)
            assert e.cause.message == "Cannot assign 3 nodes; have only 1 available"
        finally:
            await cluster_manager_handle.signal(ClusterManagerWorkflow.shutdown_cluster)
            result = await cluster_manager_handle.result()
            assert result.num_currently_assigned_nodes + result.num_bad_nodes == 24
