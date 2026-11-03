"""
Nexus operation handler implementation for the entity pattern. Each operation receives a
user_id, which is mapped to a workflow ID. The operations are synchronous because queries
and updates against a running workflow complete quickly.
"""

from __future__ import annotations

import nexusrpc
from temporalio import nexus
from temporalio.client import WorkflowHandle

from nexus_messaging.callerpattern.handler.workflows import GreetingWorkflow
from nexus_messaging.callerpattern.service import (
    ApproveInput,
    ApproveOutput,
    GetLanguageInput,
    GetLanguagesInput,
    GetLanguagesOutput,
    Language,
    NexusGreetingService,
    SetLanguageInput,
)

WORKFLOW_ID_PREFIX = "GreetingWorkflow_for_"


def get_workflow_id(user_id: str) -> str:
    """Map a user ID to a workflow ID.

    This example assumes you might have multiple workflows, one for each user.
    If you had a single workflow for all users, you could remove this function,
    remove the user_id from each input, and just use a single workflow ID.
    """
    return f"{WORKFLOW_ID_PREFIX}{user_id}"


@nexusrpc.handler.service_handler(service=NexusGreetingService)
class NexusGreetingServiceHandler:
    def _get_workflow_handle(
        self, user_id: str
    ) -> WorkflowHandle[GreetingWorkflow, str]:
        return nexus.client().get_workflow_handle_for(
            GreetingWorkflow.run, get_workflow_id(user_id)
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
            GreetingWorkflow.get_language
        )

    # Routes to set_language_using_activity (not set_language) so that new languages not
    # already in the greetings map can be fetched via an activity.
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
