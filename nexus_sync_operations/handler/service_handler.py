"""
This file demonstrates how to implement a Nexus service that is backed by a long-running workflow
and exposes operations that perform updates and queries against that workflow.
"""

from __future__ import annotations

import nexusrpc
from temporalio import nexus
from temporalio.client import Client, WorkflowHandle
from temporalio.common import WorkflowIDConflictPolicy

from message_passing.introduction import Language
from message_passing.introduction.workflows import (
    GetLanguagesInput,
    GreetingWorkflow,
    SetLanguageInput,
)
from nexus_sync_operations.service import GreetingService


@nexusrpc.handler.service_handler(service=GreetingService)
class GreetingServiceHandler:
    def __init__(self, workflow_id: str):
        self.workflow_id = workflow_id

    @classmethod
    async def create(
        cls, workflow_id: str, client: Client, task_queue: str
    ) -> GreetingServiceHandler:
        # Start the long-running "entity" workflow, if it is not already running.
        await client.start_workflow(
            GreetingWorkflow.run,
            id=workflow_id,
            task_queue=task_queue,
            id_conflict_policy=WorkflowIDConflictPolicy.USE_EXISTING,
        )
        return cls(workflow_id)

    @property
    def greeting_workflow_handle(self) -> WorkflowHandle[GreetingWorkflow, str]:
        # In nexus operation handler code, nexus.client() is always available, returning a client
        # connected to the handler namespace (it's the same client instance that your nexus worker
        # is using to poll the server for nexus tasks). This client can be used to interact with the
        # handler namespace, for example to send signals, queries, or updates. Remember however,
        # that a sync_operation handler must return quickly (no more than a few seconds). To do
        # long-running work in a nexus operation handler, use
        # temporalio.nexus.workflow_run_operation (see the hello_nexus sample).
        return nexus.client().get_workflow_handle_for(
            GreetingWorkflow.run, self.workflow_id
        )

    # 👉 This is a handler for a nexus operation whose internal implementation involves executing a
    # query against a long-running workflow that is private to the nexus service.
    @nexusrpc.handler.sync_operation
    async def get_languages(
        self, ctx: nexusrpc.handler.StartOperationContext, input: GetLanguagesInput
    ) -> list[Language]:
        return await self.greeting_workflow_handle.query(
            GreetingWorkflow.get_languages, input
        )

    # 👉 This is a handler for a nexus operation whose internal implementation involves executing a
    # query against a long-running workflow that is private to the nexus service.
    @nexusrpc.handler.sync_operation
    async def get_language(
        self, ctx: nexusrpc.handler.StartOperationContext, input: None
    ) -> Language:
        return await self.greeting_workflow_handle.query(GreetingWorkflow.get_language)

    # 👉 This is a handler for a nexus operation whose internal implementation involves executing an
    # update against a long-running workflow that is private to the nexus service. Although updates
    # can run for an arbitrarily long time, when exposing an update via a nexus sync operation the
    # update should execute quickly (sync operations must complete in under 10s).
    @nexusrpc.handler.sync_operation
    async def set_language(
        self,
        ctx: nexusrpc.handler.StartOperationContext,
        input: SetLanguageInput,
    ) -> Language:
        return await self.greeting_workflow_handle.execute_update(
            GreetingWorkflow.set_language_using_activity, input
        )
