import asyncio
from datetime import timedelta

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from service import ENDPOINTS, AsyncEchoService, EndpointResults, SyncEchoService


@workflow.defn
class EchoWorkflow:
    @workflow.run
    async def run(self, message: str) -> str:
        return message


@workflow.defn
class CallerWorkflow:
    @workflow.run
    async def run(self, message: str) -> dict[str, EndpointResults]:
        operations = []
        for endpoint in ENDPOINTS:
            sync_client = workflow.create_nexus_client(
                service=SyncEchoService, endpoint=endpoint
            )
            async_client = workflow.create_nexus_client(
                service=AsyncEchoService, endpoint=endpoint
            )
            operations.append(
                sync_client.execute_operation(
                    SyncEchoService.echo,
                    message,
                    schedule_to_close_timeout=timedelta(seconds=30),
                )
            )
            operations.append(
                async_client.execute_operation(
                    AsyncEchoService.echo_async,
                    message,
                    schedule_to_close_timeout=timedelta(seconds=30),
                )
            )
        results = await asyncio.gather(*operations)
        return {
            endpoint: EndpointResults(results[2 * index], results[2 * index + 1])
            for index, endpoint in enumerate(ENDPOINTS)
        }
