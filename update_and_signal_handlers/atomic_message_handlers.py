import asyncio
from dataclasses import dataclass
import logging
import uuid
from datetime import timedelta
from typing import Dict, List, Optional

from temporalio import activity, common, workflow
from temporalio.client import Client, WorkflowHandle
from temporalio.worker import Worker

# This samples shows off the key concurrent programming primitives for Workflows, especially
# useful for workflows that handle signals and updates.

#   - Makes signal and update handlers only operate when the workflow is within a certain state
#     (here between cluster_started and cluster_shutdown) using workflow.wait_condition.
#   - Signal and update handlers can block and their actions can be interleaved with one another and with the main workflow.
#     They should also complete before the workflow run completes.
#     Here, we use a lock to protect shared state from interleaved access.
#   - Running start_workflow with an initializer signal that you want to run before anything else.
#   - An Entity workflow that periodically "continues as new".  It must do this to prevent its history from growing too large,
#
@activity.defn
async def allocate_nodes_to_job(nodes: List[str], task_name: str) -> List[str]:
    print(f"Assigning nodes {nodes} to job {task_name}")
    await asyncio.sleep(0.1)


@activity.defn
async def deallocate_nodes_for_job(nodes: List[str], task_name: str) -> List[str]:
    print(f"Deallocating nodes {nodes} from job {task_name}")
    await asyncio.sleep(0.1)


@activity.defn
async def find_bad_nodes(nodes: List[str]) -> List[str]:
    await asyncio.sleep(0.1)
    bad_nodes = [n for n in nodes if int(n) % 5 == 0]
    if bad_nodes:
        print(f"Found bad nodes: {bad_nodes}")
    else:
        print("No new bad nodes found.")
    return bad_nodes

# In workflows that continue-as-new, it's convenient to store all your state in one serializable structure
# to make it easier to pass between runs
@dataclass(kw_only=True)
class ClusterManagerState:
    cluster_started: bool = False
    cluster_shutdown: bool = False
    nodes: Optional[Dict[str, Optional[str]]] = None
    max_assigned_nodes: int = 0
    num_assigned_nodes: int = 0

@dataclass
class ClusterManagerResult:
    max_assigned_nodes: int
    num_assigned_nodes: int

# ClusterManager keeps track of the allocations of a cluster of nodes.
# Via signals, the cluster can be started and shutdown.
# Via updates, clients can also assign jobs to nodes and delete jobs.
# These updates must run atomically.
@workflow.defn
class ClusterManager:
    def __init__(self) -> None:
        self.state = ClusterManagerState()
        # Protects workflow state from interleaved access
        self.nodes_lock = asyncio.Lock()

    @workflow.signal
    async def start_cluster(self):
        self.state.cluster_started = True
        self.state.nodes = dict([(str(k), None) for k in range(25)])
        workflow.logger.info("Cluster started")

    @workflow.signal
    async def shutdown_cluster(self):
        await workflow.wait_condition(lambda: self.state.cluster_started)
        self.state.cluster_shutdown = True
        workflow.logger.info("Cluster shut down")

    @workflow.update
    async def allocate_n_nodes_to_job(
        self,
        task_name: str,
        num_nodes: int,
    ) -> List[str]:
        await workflow.wait_condition(lambda: self.state.cluster_started)
        assert not self.state.cluster_shutdown

        await self.nodes_lock.acquire()
        try:
            unassigned_nodes = [k for k, v in self.state.nodes.items() if v is None]
            if len(unassigned_nodes) < num_nodes:
                raise ValueError(
                    f"Cannot allocate {num_nodes} nodes; have only {len(unassigned_nodes)} available"
                )
            assigned_nodes = unassigned_nodes[:num_nodes]
            # This await would be dangerous without nodes_lock because it yields control and allows interleaving.
            await self._allocate_nodes_to_job(assigned_nodes, task_name)
            self.state.max_assigned_nodes = max(
                self.state.max_assigned_nodes,
                len([k for k, v in self.state.nodes.items() if v is not None]),
            )
            return assigned_nodes
        finally:
            self.nodes_lock.release()

    async def _allocate_nodes_to_job(
        self, assigned_nodes: List[str], task_name: str
    ) -> List[str]:
        await workflow.execute_activity(
            allocate_nodes_to_job,
            args=[assigned_nodes, task_name],
            start_to_close_timeout=timedelta(seconds=10),
        )
        for node in assigned_nodes:
            self.state.nodes[node] = task_name

    @workflow.update
    async def delete_job(self, task_name: str) -> str:
        await workflow.wait_condition(lambda: self.state.cluster_started)
        assert not self.state.cluster_shutdown
        await self.nodes_lock.acquire()
        try:
            nodes_to_free = [k for k, v in self.state.nodes.items() if v == task_name]
            # This await would be dangerous without nodes_lock because it yields control and allows interleaving.
            await self._deallocate_nodes_for_job(nodes_to_free, task_name)
            return "Done"
        finally:
            self.nodes_lock.release()

    async def _deallocate_nodes_for_job(
        self, nodes_to_free: List[str], task_name: str
    ) -> List[str]:
        await workflow.execute_activity(
            deallocate_nodes_for_job,
            args=[nodes_to_free, task_name],
            start_to_close_timeout=timedelta(seconds=10),
        )
        for node in nodes_to_free:
            self.state.nodes[node] = None

    async def perform_health_checks(self):
        await self.nodes_lock.acquire()
        try:
            assigned_nodes = [k for k, v in self.state.nodes.items() if v is not None and v != "BAD!"]
            # This await would be dangerous without nodes_lock because it yields control and allows interleaving.
            bad_nodes = await workflow.execute_activity(
                find_bad_nodes,
                assigned_nodes,
                start_to_close_timeout=timedelta(seconds=10),
            )
            for node in bad_nodes:
                self.state.nodes[node] = "BAD!"
            self.state.num_assigned_nodes = len(assigned_nodes)
        finally:
            self.nodes_lock.release()

    # The cluster manager is a long-running "entity" workflow so we need to periodically checkpoint its state and 
    # continue-as-new.
    def init_from_previous_run(self, state: Optional[ClusterManagerState], max_history_length: Optional[int]):
        if state:
            self.state = state
        self.max_history_length = max_history_length

    def should_continue_as_new(self):
        # We don't want to continue-as-new if we're in the middle of an update
        if self.nodes_lock.locked():
            return False
        if workflow.info().is_continue_as_new_suggested():
            return True
        # This is just for ease-of-testing.  In production, we trust temporal to tell us when to continue as new.
        if self.max_history_length and workflow.info().get_current_history_length() > self.max_history_length:
            return True
        return False

    # max_history_size - to more conveniently test continue-as-new, not to be used in production.
    @workflow.run
    async def run(
        self,
        state: Optional[ClusterManagerState], 
        max_history_length: Optional[int]) -> ClusterManagerResult:
        self.init_from_previous_run(state, max_history_length)
        await workflow.wait_condition(lambda: self.state.cluster_started)

        # Perform health checks at intervals.  (Waking up so frequently is a bad idea in practice because it will rapidly
        # increase your workflow history size.)
        while True:
            try:
                await workflow.wait_condition(
                    lambda: self.state.cluster_shutdown or self.should_continue_as_new(), timeout=timedelta(seconds=1)
                )
            except asyncio.TimeoutError:
                pass
            if self.state.cluster_shutdown:
                break
            await self.perform_health_checks()
            if self.should_continue_as_new():
                workflow.logger.info("Continuing as new")
                await workflow.continue_as_new(args=[self.state, self.max_history_length])

        # Now we can start allocating jobs to nodes
        await workflow.wait_condition(lambda: self.state.cluster_shutdown)
        return ClusterManagerResult(self.state.max_assigned_nodes, self.state.num_assigned_nodes)


async def do_cluster_lifecycle(wf: WorkflowHandle, delay: Optional[int] = None):
    allocation_updates = []
    for i in range(6):
        allocation_updates.append(
            wf.execute_update(
                ClusterManager.allocate_n_nodes_to_job, args=[f"task-{i}", 2]
            )
        )
    await asyncio.gather(*allocation_updates)

    if delay:
        await asyncio.sleep(delay)

    deletion_updates = []
    for i in range(6):
        deletion_updates.append(
            wf.execute_update(ClusterManager.delete_job, f"task-{i}")
        )
    await asyncio.gather(*deletion_updates)

    await wf.signal(ClusterManager.shutdown_cluster)


async def main():
    client = await Client.connect("localhost:7233")

    async with Worker(
        client,
        task_queue="tq",
        workflows=[ClusterManager],
        activities=[allocate_nodes_to_job, deallocate_nodes_for_job, find_bad_nodes],
    ):
        cluster_manager_handle = await client.start_workflow(
            ClusterManager.run,
            args=[None, 150], # max_history_length to conveniently test continue-as-new
            id=f"ClusterManager-{uuid.uuid4()}",
            task_queue="tq",
            id_reuse_policy=common.WorkflowIDReusePolicy.TERMINATE_IF_RUNNING,
            start_signal="start_cluster",
        )
        await do_cluster_lifecycle(cluster_manager_handle, delay=1)
        result = await cluster_manager_handle.result()
        print(
            f"Cluster shut down successfully.  It peaked at {result.max_assigned_nodes} assigned nodes ."\
            f" It had {result.num_assigned_nodes} nodes assigned at the end."
        )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
