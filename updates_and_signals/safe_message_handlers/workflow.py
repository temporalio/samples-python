import asyncio
import dataclasses
from dataclasses import dataclass
from datetime import timedelta
from typing import Dict, List, Optional, Set

from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import ApplicationError

from updates_and_signals.safe_message_handlers.activities import (
    AssignNodesToJobInput,
    FindBadNodesInput,
    UnassignNodesForJobInput,
    assign_nodes_to_job,
    find_bad_nodes,
    unassign_nodes_for_job,
)


# In workflows that continue-as-new, it's convenient to store all your state in one serializable structure
# to make it easier to pass between runs
@dataclass
class ClusterManagerState:
    cluster_started: bool = False
    cluster_shutdown: bool = False
    nodes: Dict[str, Optional[str]] = dataclasses.field(default_factory=dict)
    jobs_assigned: Set[str] = dataclasses.field(default_factory=set)


@dataclass
class ClusterManagerInput:
    state: Optional[ClusterManagerState] = None
    test_continue_as_new: bool = False


@dataclass
class ClusterManagerResult:
    num_currently_assigned_nodes: int
    num_bad_nodes: int


# Be in the habit of storing message inputs and outputs in serializable structures.
# This makes it easier to add more over time in a backward-compatible way.
@dataclass
class ClusterManagerAssignNodesToJobInput:
    # If larger or smaller than previous amounts, will resize the job.
    total_num_nodes: int
    job_name: str


@dataclass
class ClusterManagerDeleteJobInput:
    job_name: str


@dataclass
class ClusterManagerAssignNodesToJobResult:
    nodes_assigned: Set[str]


# ClusterManagerWorkflow keeps track of the assignments of a cluster of nodes.
# Via signals, the cluster can be started and shutdown.
# Via updates, clients can also assign jobs to nodes and delete jobs.
# These updates must run atomically.
@workflow.defn
class ClusterManagerWorkflow:
    def __init__(self) -> None:
        self.state = ClusterManagerState()
        # Protects workflow state from interleaved access
        self.nodes_lock = asyncio.Lock()
        self.max_history_length: Optional[int] = None
        self.sleep_interval_seconds: int = 600

    @workflow.signal
    async def start_cluster(self) -> None:
        self.state.cluster_started = True
        self.state.nodes = {str(k): None for k in range(25)}
        workflow.logger.info("Cluster started")

    @workflow.signal
    async def shutdown_cluster(self) -> None:
        await workflow.wait_condition(lambda: self.state.cluster_started)
        self.state.cluster_shutdown = True
        workflow.logger.info("Cluster shut down")

    # This is an update as opposed to a signal because the client may want to wait for nodes to be allocated
    # before sending work to those nodes.
    # Returns the list of node names that were allocated to the job.
    @workflow.update
    async def assign_nodes_to_job(
        self, input: ClusterManagerAssignNodesToJobInput
    ) -> ClusterManagerAssignNodesToJobResult:
        await workflow.wait_condition(lambda: self.state.cluster_started)
        if self.state.cluster_shutdown:
            # If you want the client to receive a failure, either add an update validator and throw the
            # exception from there, or raise an ApplicationError. Other exceptions in the main handler
            # will cause the workflow to keep retrying and get it stuck.
            raise ApplicationError(
                "Cannot assign nodes to a job: Cluster is already shut down"
            )

        async with self.nodes_lock:
            # Idempotency guard.
            if input.job_name in self.state.jobs_assigned:
                return ClusterManagerAssignNodesToJobResult(
                    self.get_assigned_nodes(job_name=input.job_name)
                )
            unassigned_nodes = self.get_unassigned_nodes()
            if len(unassigned_nodes) < input.total_num_nodes:
                # If you want the client to receive a failure, either add an update validator and throw the
                # exception from there, or raise an ApplicationError. Other exceptions in the main handler
                # will cause the workflow to keep retrying and get it stuck.
                raise ApplicationError(
                    f"Cannot assign {input.total_num_nodes} nodes; have only {len(unassigned_nodes)} available"
                )
            nodes_to_assign = unassigned_nodes[: input.total_num_nodes]
            # This await would be dangerous without nodes_lock because it yields control and allows interleaving
            # with delete_job and perform_health_checks, which both touch self.state.nodes.
            await self._assign_nodes_to_job(nodes_to_assign, input.job_name)
            return ClusterManagerAssignNodesToJobResult(
                nodes_assigned=self.get_assigned_nodes(job_name=input.job_name)
            )

    async def _assign_nodes_to_job(
        self, assigned_nodes: List[str], job_name: str
    ) -> None:
        await workflow.execute_activity(
            assign_nodes_to_job,
            AssignNodesToJobInput(nodes=assigned_nodes, job_name=job_name),
            start_to_close_timeout=timedelta(seconds=10),
        )
        for node in assigned_nodes:
            self.state.nodes[node] = job_name
        self.state.jobs_assigned.add(job_name)

    # Even though it returns nothing, this is an update because the client may want to track it, for example
    # to wait for nodes to be unassignd before reassigning them.
    @workflow.update
    async def delete_job(self, input: ClusterManagerDeleteJobInput) -> None:
        await workflow.wait_condition(lambda: self.state.cluster_started)
        if self.state.cluster_shutdown:
            # If you want the client to receive a failure, either add an update validator and throw the
            # exception from there, or raise an ApplicationError. Other exceptions in the main handler
            # will cause the workflow to keep retrying and get it stuck.
            raise ApplicationError("Cannot delete a job: Cluster is already shut down")

        async with self.nodes_lock:
            nodes_to_unassign = [
                k for k, v in self.state.nodes.items() if v == input.job_name
            ]
            # This await would be dangerous without nodes_lock because it yields control and allows interleaving
            # with assign_nodes_to_job and perform_health_checks, which all touch self.state.nodes.
            await self._unassign_nodes_for_job(nodes_to_unassign, input.job_name)

    async def _unassign_nodes_for_job(
        self, nodes_to_unassign: List[str], job_name: str
    ):
        await workflow.execute_activity(
            unassign_nodes_for_job,
            UnassignNodesForJobInput(nodes=nodes_to_unassign, job_name=job_name),
            start_to_close_timeout=timedelta(seconds=10),
        )
        for node in nodes_to_unassign:
            self.state.nodes[node] = None

    def get_unassigned_nodes(self) -> List[str]:
        return [k for k, v in self.state.nodes.items() if v is None]

    def get_bad_nodes(self) -> Set[str]:
        return set([k for k, v in self.state.nodes.items() if v == "BAD!"])

    def get_assigned_nodes(self, *, job_name: Optional[str] = None) -> Set[str]:
        if job_name:
            return set([k for k, v in self.state.nodes.items() if v == job_name])
        else:
            return set(
                [
                    k
                    for k, v in self.state.nodes.items()
                    if v is not None and v != "BAD!"
                ]
            )

    async def perform_health_checks(self) -> None:
        async with self.nodes_lock:
            assigned_nodes = self.get_assigned_nodes()
            try:
                # This await would be dangerous without nodes_lock because it yields control and allows interleaving
                # with assign_nodes_to_job and delete_job, which both touch self.state.nodes.
                bad_nodes = await workflow.execute_activity(
                    find_bad_nodes,
                    FindBadNodesInput(nodes_to_check=assigned_nodes),
                    start_to_close_timeout=timedelta(seconds=10),
                    # This health check is optional, and our lock would block the whole workflow if we let it retry forever.
                    retry_policy=RetryPolicy(maximum_attempts=1),
                )
                for node in bad_nodes:
                    self.state.nodes[node] = "BAD!"
            except Exception as e:
                workflow.logger.warn(
                    f"Health check failed with error {type(e).__name__}:{e}"
                )

    # The cluster manager is a long-running "entity" workflow so we need to periodically checkpoint its state and
    # continue-as-new.
    def init(self, input: ClusterManagerInput) -> None:
        if input.state:
            self.state = input.state
        if input.test_continue_as_new:
            self.max_history_length = 120
            self.sleep_interval_seconds = 1

    def should_continue_as_new(self) -> bool:
        if workflow.info().is_continue_as_new_suggested():
            return True
        # This is just for ease-of-testing.  In production, we trust temporal to tell us when to continue as new.
        if (
            self.max_history_length
            and workflow.info().get_current_history_length() > self.max_history_length
        ):
            return True
        return False

    @workflow.run
    async def run(self, input: ClusterManagerInput) -> ClusterManagerResult:
        self.init(input)
        await workflow.wait_condition(lambda: self.state.cluster_started)
        # Perform health checks at intervals.
        while True:
            await self.perform_health_checks()
            try:
                await workflow.wait_condition(
                    lambda: self.state.cluster_shutdown
                    or self.should_continue_as_new(),
                    timeout=timedelta(seconds=self.sleep_interval_seconds),
                )
            except asyncio.TimeoutError:
                pass
            if self.state.cluster_shutdown:
                break
            if self.should_continue_as_new():
                # We don't want to leave any job assignment or deletion handlers half-finished when we continue as new.
                await workflow.wait_condition(lambda: workflow.all_handlers_finished())
                workflow.logger.info("Continuing as new")
                workflow.continue_as_new(
                    ClusterManagerInput(
                        state=self.state,
                        test_continue_as_new=input.test_continue_as_new,
                    )
                )
        # Make sure we finish off handlers such as deleting jobs before we complete the workflow.
        await workflow.wait_condition(lambda: workflow.all_handlers_finished())
        return ClusterManagerResult(
            len(self.get_assigned_nodes()),
            len(self.get_bad_nodes()),
        )
