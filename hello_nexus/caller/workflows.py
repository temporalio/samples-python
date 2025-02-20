from datetime import timedelta

from temporalio import workflow
from temporalio.exceptions import FailureError
from temporalio.workflow import NexusClient

from hello_nexus.service.interface import (
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
            "my-nexus-endpoint-name",
            schedule_to_close_timeout=timedelta(seconds=30),
        )


@workflow.defn
class EchoCallerWorkflow(CallerWorkflowBase):
    @workflow.run
    async def run(self, message: str) -> EchoOutput:
        op_output = await self.nexus_client.execute_operation(
            MyNexusService.echo,
            EchoInput(message),
        )
        return op_output


@workflow.defn
class Echo2CallerWorkflow(CallerWorkflowBase):
    @workflow.run
    async def run(self, message: str) -> EchoOutput:
        op_output = await self.nexus_client.execute_operation(
            MyNexusService.echo2,
            EchoInput(message),
        )
        return op_output


@workflow.defn
class Echo3CallerWorkflow(CallerWorkflowBase):
    @workflow.run
    async def run(self, message: str) -> EchoOutput:
        op_output = await self.nexus_client.execute_operation(
            MyNexusService.echo3,
            EchoInput(message),
        )
        return op_output


@workflow.defn
class HelloCallerWorkflow(CallerWorkflowBase):
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
    @workflow.run
    async def run(self, name: str) -> HelloOutput:
        handle = await self.nexus_client.start_operation(
            MyNexusService.hello2,
            HelloInput(name),
        )
        return await handle


@workflow.defn
class Hello3CallerWorkflow(CallerWorkflowBase):
    @workflow.run
    async def run(self, name: str) -> HelloOutput:
        handle = await self.nexus_client.start_operation(
            MyNexusService.hello3,
            HelloInput(name),
        )
        return await handle
