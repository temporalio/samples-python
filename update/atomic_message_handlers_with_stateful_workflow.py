import asyncio
from datetime import timedelta
import logging
from typing import Dict, List, Optional

from temporalio import activity, common, workflow
from temporalio.client import Client, WorkflowHandle
from temporalio.worker import Worker

@activity.defn
async def allocate_nodes_to_job(nodes: List[int], task_name: str) -> List[int]:
    print(f"Assigning nodes {nodes} to job {task_name}")
    await asyncio.sleep(0.1)

@activity.defn
async def deallocate_nodes_for_job(nodes: List[int], task_name: str) -> List[int]:
    print(f"Deallocating nodes {nodes} from job {task_name}")
    await asyncio.sleep(0.1)

@activity.defn
async def find_bad_nodes(nodes: List[int]) -> List[int]:
    await asyncio.sleep(0.1)
    bad_nodes = [n for n in nodes if n % 5 == 0]
    print(f"Found bad nodes: {bad_nodes}")
    return bad_nodes

# This samples shows off
#   - Making signal and update handlers only operate when the workflow is within a certain state 
#     (here between cluster_started and cluster_shutdown)
#   - Using a lock to protect shared state shared by the workflow and its signal and update handlers
#     interleaving writes
#   - Running start_workflow with an initializer signal that you want to run before anything else.
@workflow.defn
class ClusterManager:
    def __init__(self) -> None:
        self.cluster_started = False
        self.cluster_shutdown = False
        self.nodes_lock = asyncio.Lock()

    @workflow.signal
    async def start_cluster(self):
        self.cluster_started = True
        self.nodes : Dict[Optional[str]] = dict([(k, None) for k in range(25)])
        workflow.logger.info("Cluster started")

    @workflow.signal
    async def shutdown_cluster(self):
        await workflow.wait_condition(lambda: self.cluster_started)
        self.cluster_shutdown = True
        workflow.logger.info("Cluster shut down")

    @workflow.update
    async def allocate_n_nodes_to_job(self, task_name: str, num_nodes: int, ) -> List[int]:
        await workflow.wait_condition(lambda: self.cluster_started)
        assert not self.cluster_shutdown

        await self.nodes_lock.acquire()
        try:
            unassigned_nodes = [k for k, v in self.nodes.items() if v is None]
            if len(unassigned_nodes) < num_nodes:
                raise ValueError(f"Cannot allocate {num_nodes} nodes; have only {len(unassigned_nodes)} available")
            assigned_nodes = unassigned_nodes[:num_nodes]
            await self._allocate_nodes_to_job(assigned_nodes, task_name)
            return assigned_nodes
        finally:
            self.nodes_lock.release()

    
    async def _allocate_nodes_to_job(self, assigned_nodes: List[int], task_name: str) -> List[int]:
        await workflow.execute_activity(
            allocate_nodes_to_job, args=[assigned_nodes, task_name], start_to_close_timeout=timedelta(seconds=10)
        )
        for node in assigned_nodes:
            self.nodes[node] = task_name


    @workflow.update
    async def delete_job(self, task_name: str) -> str:
        await workflow.wait_condition(lambda: self.cluster_started)
        assert not self.cluster_shutdown
        await self.nodes_lock.acquire()
        try:
            nodes_to_free = [k for k, v in self.nodes.items() if v == task_name]
            await self._deallocate_nodes_for_job(nodes_to_free, task_name) 
            return "Done"
        finally:
            self.nodes_lock.release()

    async def _deallocate_nodes_for_job(self, nodes_to_free: List[int], task_name: str) -> List[int]:
        await workflow.execute_activity(
            deallocate_nodes_for_job, args=[nodes_to_free, task_name], start_to_close_timeout=timedelta(seconds=10)
        )
        for node in nodes_to_free:
            self.nodes[node] = None


    @workflow.update
    async def resize_job(self, task_name: str, new_size: int) -> List[int]:
        await workflow.wait_condition(lambda: self.cluster_started)
        assert not self.cluster_shutdown
        await self.nodes_lock.acquire()
        try:
            allocated_nodes = [k for k, v in self.nodes.items() if v == task_name]
            delta = new_size - len(allocated_nodes)
            if delta == 0:
                return allocated_nodes
            elif delta > 0:
                unassigned_nodes = [k for k, v in self.nodes.items() if v is None]
                if len(unassigned_nodes) < delta:
                    raise ValueError(f"Cannot allocate {delta} nodes; have only {len(unassigned_nodes)} available")
                nodes_to_assign = unassigned_nodes[:delta]
                await self._allocate_nodes_to_job(nodes_to_assign, task_name)
                return allocated_nodes + nodes_to_assign
            else:
                nodes_to_deallocate = allocated_nodes[delta:]
                await self._deallocate_nodes_for_job(nodes_to_deallocate, task_name)
                return list(filter(lambda x: x not in nodes_to_deallocate, allocated_nodes))
        finally:
            self.nodes_lock.release()

    async def perform_health_checks(self):
        await self.nodes_lock.acquire()
        try:
            assigned_nodes = [k for k, v in self.nodes.items() if v is not None]
            bad_nodes = await workflow.execute_activity(find_bad_nodes, assigned_nodes, start_to_close_timeout=timedelta(seconds=10))
            for node in bad_nodes:
                self.nodes[node] = "BAD!"
        finally:
            self.nodes_lock.release()

    @workflow.run
    async def run(self):
        await workflow.wait_condition(lambda: self.cluster_started)

        while True:
            try:
                await workflow.wait_condition(lambda: self.cluster_shutdown, timeout=timedelta(seconds=1))
            except asyncio.TimeoutError:
                pass
            await self.perform_health_checks()

        # Now we can start allocating jobs to nodes
        await workflow.wait_condition(lambda: self.cluster_shutdown)


async def do_cluster_lifecycle(wf: WorkflowHandle):

    allocation_updates = []
    for i in range(6):
        allocation_updates.append(wf.execute_update(ClusterManager.allocate_n_nodes_to_job, args=[f"task-{i}", 2]))
    await asyncio.gather(*allocation_updates)        
    
    resize_updates = []
    for i in range(6):
        resize_updates.append(wf.execute_update(ClusterManager.resize_job, args=[f"task-{i}", 4]))
    await asyncio.gather(*resize_updates)

    deletion_updates = []
    for i in range(6):
        deletion_updates.append(wf.execute_update(ClusterManager.delete_job, f"task-{i}"))
    await asyncio.gather(*deletion_updates)
        
    await wf.signal(ClusterManager.shutdown_cluster)
    print("Cluster shut down")
    


async def main():
    client = await Client.connect("localhost:7233")

    async with Worker(
        client,
        task_queue="tq",
        workflows=[ClusterManager],
        activities=[allocate_nodes_to_job, deallocate_nodes_for_job, find_bad_nodes],
    ):
        wf = await client.start_workflow(
            ClusterManager.run,
            id="wid",
            task_queue="tq",
            id_reuse_policy=common.WorkflowIDReusePolicy.TERMINATE_IF_RUNNING,
            start_signal='start_cluster',

        )
        await do_cluster_lifecycle(wf)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())


            