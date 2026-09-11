"""
Nexus operation handler for the on-demand pattern. Each operation receives the target
user_id in its input, and run_from_remote starts a brand-new GreetingWorkflow. Operations
use Temporal operation handlers so the SDK can manage their lifecycle and link the caller's
Nexus operation to the target Workflow.
"""

from __future__ import annotations

import nexusrpc
from temporalio import nexus
from temporalio.client import Client, WorkflowHandle
from temporalio.common import WorkflowIDConflictPolicy

from nexus_messaging.ondemandpattern.handler.workflows import (
    ATTACH_APPROVAL_CONTEXT_SIGNAL,
    GreetingWorkflow,
)
from nexus_messaging.ondemandpattern.service import (
    ApproveInput,
    ApproveOutput,
    AttachApprovalContextInput,
    GetLanguageInput,
    GetLanguagesInput,
    GetLanguagesOutput,
    Language,
    NexusRemoteGreetingService,
    RunFromRemoteInput,
    SetLanguageInput,
)

WORKFLOW_ID_PREFIX = "GreetingWorkflow_for_"


@nexusrpc.handler.service_handler(service=NexusRemoteGreetingService)
class NexusRemoteGreetingServiceHandler:
    def _get_workflow_id(self, user_id: str) -> str:
        return WORKFLOW_ID_PREFIX + user_id

    def _get_workflow_handle(
        self, client: Client, user_id: str
    ) -> WorkflowHandle[GreetingWorkflow, str]:
        return client.get_workflow_handle_for(
            GreetingWorkflow.run, self._get_workflow_id(user_id)
        )

    # Starts a new GreetingWorkflow with the caller-specified user ID,
    # or attached to one already running.
    # This is an async Nexus operation backed by temporal_operation.
    @nexus.temporal_operation
    async def run_from_remote(
        self,
        _ctx: nexus.TemporalStartOperationContext,
        client: nexus.TemporalNexusClient,
        input: RunFromRemoteInput,
    ) -> nexus.TemporalOperationResult[str]:
        return await client.start_workflow(
            GreetingWorkflow.run,
            id=self._get_workflow_id(input.user_id),
            # Since attach_approval_context can create the GreetingWorkflow first,
            # this operation needs to attach to the running execution rather than
            # fail (default behavior).
            id_conflict_policy=WorkflowIDConflictPolicy.USE_EXISTING,
        )

    @nexus.temporal_operation
    async def get_languages(
        self,
        _ctx: nexus.TemporalStartOperationContext,
        client: nexus.TemporalNexusClient,
        input: GetLanguagesInput,
    ) -> nexus.TemporalOperationResult[GetLanguagesOutput]:
        result = await self._get_workflow_handle(client.client, input.user_id).query(
            GreetingWorkflow.get_languages, input
        )
        return nexus.TemporalOperationResult.sync(result)

    @nexus.temporal_operation
    async def get_language(
        self,
        _ctx: nexus.TemporalStartOperationContext,
        client: nexus.TemporalNexusClient,
        input: GetLanguageInput,
    ) -> nexus.TemporalOperationResult[Language]:
        result = await self._get_workflow_handle(client.client, input.user_id).query(
            GreetingWorkflow.get_language,
        )
        return nexus.TemporalOperationResult.sync(result)

    # Routes to set_language_using_activity so that new languages not already in the
    # greetings map can be fetched via an activity.
    @nexus.temporal_operation
    async def set_language(
        self,
        _ctx: nexus.TemporalStartOperationContext,
        client: nexus.TemporalNexusClient,
        input: SetLanguageInput,
    ) -> nexus.TemporalOperationResult[Language]:
        return await client.start_workflow_update(
            self._get_workflow_id(input.user_id),
            GreetingWorkflow.set_language_using_activity,
            input,
        )

    @nexus.temporal_operation
    async def approve(
        self,
        _ctx: nexus.TemporalStartOperationContext,
        client: nexus.TemporalNexusClient,
        input: ApproveInput,
    ) -> nexus.TemporalOperationResult[ApproveOutput]:
        await self._get_workflow_handle(client.client, input.user_id).signal(
            GreetingWorkflow.approve, input
        )
        return nexus.TemporalOperationResult.sync(ApproveOutput())

    # Signals a Workflow, starting the Workflow first if it is not already running.
    @nexus.temporal_operation
    async def attach_approval_context(
        self,
        _ctx: nexus.TemporalStartOperationContext,
        client: nexus.TemporalNexusClient,
        input: AttachApprovalContextInput,
    ) -> nexus.TemporalOperationResult[None]:
        await client.client.start_workflow(
            GreetingWorkflow.run,
            id=self._get_workflow_id(input.user_id),
            task_queue=nexus.info().task_queue,
            start_signal=ATTACH_APPROVAL_CONTEXT_SIGNAL,
            start_signal_args=[input],
        )
        return nexus.TemporalOperationResult.sync(None)
