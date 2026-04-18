"""Nexus service handler and backing workflow for standalone operations sample."""

from __future__ import annotations

import uuid

import nexusrpc.handler
from temporalio import nexus, workflow

from nexus_standalone_operations.service import (
    EchoInput,
    EchoOutput,
    HelloInput,
    HelloOutput,
    MyNexusService,
)


@workflow.defn
class HelloWorkflow:
    @workflow.run
    async def run(self, input: HelloInput) -> HelloOutput:
        return HelloOutput(greeting=f"Hello, {input.name}!")


@nexusrpc.handler.service_handler(service=MyNexusService)
class MyNexusServiceHandler:
    @nexusrpc.handler.sync_operation
    async def echo(
        self, _ctx: nexusrpc.handler.StartOperationContext, input: EchoInput
    ) -> EchoOutput:
        return EchoOutput(message=input.message)

    @nexus.workflow_run_operation
    async def hello(
        self, ctx: nexus.WorkflowRunOperationContext, input: HelloInput
    ) -> nexus.WorkflowHandle[HelloOutput]:
        return await ctx.start_workflow(
            HelloWorkflow.run,
            input,
            id=str(uuid.uuid4()),
        )
