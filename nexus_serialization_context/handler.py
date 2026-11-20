import nexusrpc.handler
from temporalio import nexus

from service import AsyncEchoService, SyncEchoService
from workflows import EchoWorkflow


@nexusrpc.handler.service_handler(service=SyncEchoService)
class SyncEchoHandler:
    @nexusrpc.handler.sync_operation
    async def echo(
        self, ctx: nexusrpc.handler.StartOperationContext, message: str
    ) -> str:
        return message


@nexusrpc.handler.service_handler(service=AsyncEchoService)
class AsyncEchoHandler:
    @nexus.workflow_run_operation(name="echoAsync")
    async def echo_async(
        self, ctx: nexus.WorkflowRunOperationContext, message: str
    ) -> nexus.WorkflowHandle[str]:
        # Retries reuse this ID. Separate operations get separate backing workflows.
        return await ctx.start_workflow(
            EchoWorkflow.run, message, id=f"nexus-echo-{ctx.request_id}"
        )
