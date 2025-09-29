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
    # This nexus service is backed by a long-running "entity" workflow. This means that the workflow
    # is always running in the background, allowing the service to be stateful and durable. The
    # service interacts with it via messages (updates and queries). All of this is implementation
    # detail private to the nexus handler: the nexus caller does not know how the operations are
    # implemented or what is providing the backing storage.
    LONG_RUNNING_WORKFLOW_ID = "nexus-sync-operations-greeting-workflow"

    @classmethod
    async def start(cls, client: Client, task_queue: str) -> None:
        # Start the long-running "entity" workflow, if it is not already running.
        await client.start_workflow(
            GreetingWorkflow.run,
            id=cls.LONG_RUNNING_WORKFLOW_ID,
            task_queue=task_queue,
            id_conflict_policy=WorkflowIDConflictPolicy.USE_EXISTING,
        )

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
            GreetingWorkflow.run, self.LONG_RUNNING_WORKFLOW_ID
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
    # update against a long-running workflow that is private to the nexus service.
    @nexusrpc.handler.sync_operation
    async def set_language(
        self,
        ctx: nexusrpc.handler.StartOperationContext,
        input: SetLanguageInput,
    ) -> Language:
        return await self.greeting_workflow_handle.execute_update(
            GreetingWorkflow.set_language_using_activity, input
        )
