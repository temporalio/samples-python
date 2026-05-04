"""
Nexus operation handler for the on-demand pattern. Each operation receives the target
userId in its input, and run_from_remote starts a brand-new GreetingWorkflow.
"""

from __future__ import annotations

import nexusrpc
from temporalio import nexus
from temporalio.client import WorkflowHandle

from nexus_messaging.ondemandpattern.handler.workflows import GreetingWorkflow
from nexus_messaging.ondemandpattern.service import (
    ApproveInput,
    ApproveOutput,
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
        self, user_id: str
    ) -> WorkflowHandle[GreetingWorkflow, str]:
        return nexus.client().get_workflow_handle_for(
            GreetingWorkflow.run, self._get_workflow_id(user_id)
        )

    # Starts a new GreetingWorkflow with the caller-specified user ID.
    # This is an async Nexus operation backed by workflow_run_operation.
    @nexus.workflow_run_operation
    async def run_from_remote(
        self, ctx: nexus.WorkflowRunOperationContext, input: RunFromRemoteInput
    ) -> nexus.WorkflowHandle[str]:
        return await ctx.start_workflow(
            GreetingWorkflow.run,
            id=self._get_workflow_id(input.user_id),
        )

    @nexusrpc.handler.sync_operation
    async def get_languages(
        self, ctx: nexusrpc.handler.StartOperationContext, input: GetLanguagesInput
    ) -> GetLanguagesOutput:
        return await self._get_workflow_handle(input.user_id).query(
            GreetingWorkflow.get_languages, input
        )

    @nexusrpc.handler.sync_operation
    async def get_language(
        self, ctx: nexusrpc.handler.StartOperationContext, input: GetLanguageInput
    ) -> Language:
        return await self._get_workflow_handle(input.user_id).query(
            GreetingWorkflow.get_language,
        )

    # Routes to set_language_using_activity so that new languages not already in the
    # greetings map can be fetched via an activity.
    @nexusrpc.handler.sync_operation
    async def set_language(
        self, ctx: nexusrpc.handler.StartOperationContext, input: SetLanguageInput
    ) -> Language:
        return await self._get_workflow_handle(input.user_id).execute_update(
            GreetingWorkflow.set_language_using_activity, input
        )

    @nexusrpc.handler.sync_operation
    async def approve(
        self, ctx: nexusrpc.handler.StartOperationContext, input: ApproveInput
    ) -> ApproveOutput:
        await self._get_workflow_handle(input.user_id).signal(
            GreetingWorkflow.approve, input
        )
        return ApproveOutput()
