from datetime import timedelta

import xray
from temporalio import workflow
from temporalio.exceptions import FailureError
from temporalio.workflow import NexusClient

from hello_nexus.handler.nexus_service import (
    EchoInput,
    EchoOutput,
    HelloInput,
    HelloOutput,
    MyNexusService,
)


class CallerWorkflowBase:
    def __init__(self):
        self.nexus_client = NexusClient(
            MyNexusService,  # or string name "my-nexus-service",
            "my-nexus-endpoint-name-python",
            schedule_to_close_timeout=timedelta(seconds=30),
        )


@workflow.defn
class EchoCallerWorkflow(CallerWorkflowBase):
    @xray.start_as_current_workflow_method_span()
    @workflow.run
    async def run(self, message: str) -> EchoOutput:
        op_output = await self.nexus_client.execute_operation(
            MyNexusService.echo,
            EchoInput(message),
        )
        return op_output


@workflow.defn
class Echo2CallerWorkflow(CallerWorkflowBase):
    @xray.start_as_current_workflow_method_span()
    @workflow.run
    async def run(self, message: str) -> EchoOutput:
        op_output = await self.nexus_client.execute_operation(
            MyNexusService.echo2,
            EchoInput(message),
        )
        return op_output


@workflow.defn
class Echo3CallerWorkflow(CallerWorkflowBase):
    @xray.start_as_current_workflow_method_span()
    @workflow.run
    async def run(self, message: str) -> EchoOutput:
        op_output = await self.nexus_client.execute_operation(
            MyNexusService.echo3,
            EchoInput(message),
        )
        return op_output


@workflow.defn
class HelloCallerWorkflow(CallerWorkflowBase):
    @xray.start_as_current_workflow_method_span()
    @workflow.run
    async def run(self, name: str) -> HelloOutput:
        handle = await self.nexus_client.start_operation(
            MyNexusService.hello,
            HelloInput(name),
        )
        assert handle.cancel()
        try:
            await handle
        except FailureError:
            handle = await self.nexus_client.start_operation(
                MyNexusService.hello,
                HelloInput(name),
            )
            result = await handle
            return result
        raise AssertionError("Expected Nexus operation to be cancelled")


@workflow.defn
class Hello2CallerWorkflow(CallerWorkflowBase):
    @xray.start_as_current_workflow_method_span()
    @workflow.run
    async def run(self, name: str) -> HelloOutput:
        handle = await self.nexus_client.start_operation(
            MyNexusService.hello2,
            HelloInput(name),
        )
        return await handle
