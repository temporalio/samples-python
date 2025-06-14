from datetime import timedelta

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from trio_async.activities import say_hello_activity_async, say_hello_activity_sync


@workflow.defn
class SayHelloWorkflow:
    @workflow.run
    async def run(self, name: str) -> list[str]:
        # Workflows don't use default asyncio event loop or Trio, they use a
        # custom event loop. Therefore Trio primitives should never be used in a
        # workflow, only asyncio helpers (which delegate to the custom loop).
        return [
            # That these are two different activities for async or sync means
            # nothing to the workflow, we just have both to demonstrate the
            # activity side
            await workflow.execute_activity(
                say_hello_activity_async,
                name,
                start_to_close_timeout=timedelta(minutes=5),
            ),
            await workflow.execute_activity(
                say_hello_activity_sync,
                name,
                start_to_close_timeout=timedelta(minutes=5),
            ),
        ]
