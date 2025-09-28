"""
This file demonstrates how to implement a Nexus service that is backed by a long-running
workflow and exposes operations that perform signals, updates, and queries against that
workflow.
"""

from __future__ import annotations

import nexusrpc
from temporalio import nexus
from temporalio.client import Client, WorkflowHandle
from temporalio.common import WorkflowIDConflictPolicy

from message_passing.introduction import Language
from message_passing.introduction.workflows import (
    ApproveInput,
    GetLanguagesInput,
    GreetingWorkflow,
    SetLanguageInput,
    SetLanguageUsingActivityInput,
)
from nexus_sync_operations.service import GreetingService


@nexusrpc.handler.service_handler(service=GreetingService)
class GreetingServiceHandler:
    def __init__(
        self,
        greeting_workflow_handle: WorkflowHandle[GreetingWorkflow, str],
    ):
        self.greeting_workflow_handle = greeting_workflow_handle

    @classmethod
    async def create(cls, client: Client, task_queue: str) -> GreetingServiceHandler:
        # Obtain a workflow handle to the long-running workflow that backs this service, starting
        # the workflow if it is not already running.
        return cls(await cls._get_workflow_handle(client, task_queue))

    @staticmethod
    async def _get_workflow_handle(
        client: Client, task_queue: str
    ) -> WorkflowHandle[GreetingWorkflow, str]:
        return await client.start_workflow(
            GreetingWorkflow.run,
            id="nexus-sync-operations-greeting-workflow",
            task_queue=task_queue,
            id_conflict_policy=WorkflowIDConflictPolicy.USE_EXISTING,
        )

    @nexusrpc.handler.sync_operation
    async def get_languages(
        self, ctx: nexusrpc.handler.StartOperationContext, input: GetLanguagesInput
    ) -> list[Language]:
        return await self.greeting_workflow_handle.query(
            GreetingWorkflow.get_languages, input
        )

    @nexusrpc.handler.sync_operation
    async def get_language(
        self, ctx: nexusrpc.handler.StartOperationContext, input: None
    ) -> Language:
        return await self.greeting_workflow_handle.query(GreetingWorkflow.get_language)

    @nexusrpc.handler.sync_operation
    async def set_language(
        self, ctx: nexusrpc.handler.StartOperationContext, input: SetLanguageInput
    ) -> Language:
        return await self.greeting_workflow_handle.execute_update(
            GreetingWorkflow.set_language, input.language
        )

    @nexusrpc.handler.sync_operation
    async def set_language_using_activity(
        self,
        ctx: nexusrpc.handler.StartOperationContext,
        input: SetLanguageUsingActivityInput,
    ) -> Language:
        return await self.greeting_workflow_handle.execute_update(
            GreetingWorkflow.set_language_using_activity, input.language
        )

    @nexusrpc.handler.sync_operation
    async def approve(
        self, ctx: nexusrpc.handler.StartOperationContext, input: ApproveInput
    ) -> None:
        await self.greeting_workflow_handle.signal(GreetingWorkflow.approve, input)
        self.greeting_workflow_handle = await self._get_workflow_handle(
            nexus.client(), nexus.info().task_queue
        )
