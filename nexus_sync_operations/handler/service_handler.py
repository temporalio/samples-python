"""
This file demonstrates how to implement a Nexus service that is backed by an entity workflow
and exposes operations that perform queries, updates, signals, and signal-with-start operations
against that workflow.

The entity workflow follows the entity pattern: it runs indefinitely, processes operations
as they arrive, and periodically continues-as-new to prevent history growth.
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
    SetLanguageInput,
)
from nexus_sync_operations.handler.workflows import GreetingEntityWorkflow
from nexus_sync_operations.service import GreetingService


@nexusrpc.handler.service_handler(service=GreetingService)
class GreetingServiceHandler:
    def __init__(self, workflow_id: str, task_queue: str):
        self.workflow_id = workflow_id
        self.task_queue = task_queue

    @classmethod
    async def create(
        cls, workflow_id: str, client: Client, task_queue: str
    ) -> GreetingServiceHandler:
        # Start the long-running "entity" workflow, if it is not already running.
        # Entity workflows run indefinitely and process operations as they arrive.
        await client.start_workflow(
            GreetingEntityWorkflow.run,
            id=workflow_id,
            task_queue=task_queue,
            id_conflict_policy=WorkflowIDConflictPolicy.USE_EXISTING,
        )
        return cls(workflow_id, task_queue)

    @property
    def greeting_workflow_handle(self) -> WorkflowHandle[GreetingEntityWorkflow, None]:
        # In nexus operation handler code, nexus.client() is always available, returning a client
        # connected to the handler namespace (it's the same client instance that your nexus worker
        # is using to poll the server for nexus tasks). This client can be used to interact with the
        # handler namespace, for example to send signals, queries, or updates. Remember however,
        # that a sync_operation handler must return quickly (no more than a few seconds). To do
        # long-running work in a nexus operation handler, use
        # temporalio.nexus.workflow_run_operation (see the hello_nexus sample).
        return nexus.client().get_workflow_handle_for(
            GreetingEntityWorkflow.run, self.workflow_id
        )

    # 👉 This is a handler for a nexus operation whose internal implementation involves executing a
    # query against a long-running workflow that is private to the nexus service.
    @nexusrpc.handler.sync_operation
    async def get_languages(
        self, ctx: nexusrpc.handler.StartOperationContext, input: GetLanguagesInput
    ) -> list[Language]:
        return await self.greeting_workflow_handle.query(
            GreetingEntityWorkflow.get_languages, input
        )

    # 👉 This is a handler for a nexus operation whose internal implementation involves executing a
    # query against a long-running workflow that is private to the nexus service.
    @nexusrpc.handler.sync_operation
    async def get_language(
        self, ctx: nexusrpc.handler.StartOperationContext, input: None
    ) -> Language:
        return await self.greeting_workflow_handle.query(GreetingEntityWorkflow.get_language)

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
            GreetingEntityWorkflow.set_language_using_activity, input
        )

    # 👉 This is a handler for a nexus operation whose internal implementation involves executing a
    # synchronous update (non-async) against a long-running workflow.
    @nexusrpc.handler.sync_operation
    async def set_language_sync(
        self,
        ctx: nexusrpc.handler.StartOperationContext,
        input: SetLanguageInput,
    ) -> Language:
        return await self.greeting_workflow_handle.execute_update(
            GreetingEntityWorkflow.set_language, input
        )

    # 👉 This is a handler for a nexus operation whose internal implementation involves sending a
    # signal to a long-running workflow that is private to the nexus service.
    @nexusrpc.handler.sync_operation
    async def approve(
        self,
        ctx: nexusrpc.handler.StartOperationContext,
        input: ApproveInput,
    ) -> None:
        await self.greeting_workflow_handle.signal(
            GreetingEntityWorkflow.approve, input
        )

    # 👉 This is a handler for a nexus operation whose internal implementation involves sending a
    # signal-with-start to a long-running workflow. If the workflow doesn't exist, it will be started.
    @nexusrpc.handler.sync_operation
    async def approve_with_start(
        self,
        ctx: nexusrpc.handler.StartOperationContext,
        input: ApproveInput,
    ) -> None:
        # Use signal_with_start synchronously - send signal and start workflow if needed
        await nexus.client().start_workflow(
            GreetingEntityWorkflow.run,
            id=self.workflow_id,
            task_queue=self.task_queue,
            start_signal=GreetingEntityWorkflow.approve,
            start_signal_args=[input],
            id_conflict_policy=WorkflowIDConflictPolicy.USE_EXISTING,
        )
