from datetime import timedelta

import nexusrpc
from temporalio import workflow
from temporalio.workflow import NexusClient


@nexusrpc.handler.service
class MyNexusService:
    @nexusrpc.handler.sync_operation
    async def my_op(self, input: str, _: nexusrpc.handler.StartOperationOptions) -> str:
        return f"{input}-result"


@workflow.defn
class Workflow:
    @workflow.run
    async def run(self, message: str) -> str:
        nexus_client = NexusClient(
            MyNexusService,
            "my-endpoint",
            schedule_to_close_timeout=timedelta(seconds=30),
        )
        return await nexus_client.execute_operation(MyNexusService.my_op, message)
