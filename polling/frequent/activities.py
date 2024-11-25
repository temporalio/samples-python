import asyncio

from temporalio import activity

from polling.test_service import ComposeGreetingInput, get_service_result


@activity.defn
async def compose_greeting(input: ComposeGreetingInput) -> str:
    while True:
        try:
            try:
                result = await get_service_result(input)
                activity.logger.info(f"Exiting activity ${result}")
                return result
            except Exception:
                # swallow exception since service is down
                activity.logger.debug("Failed, trying again shortly", exc_info=True)

            activity.heartbeat("Invoking activity")
            await asyncio.sleep(1)
        except asyncio.CancelledError:
            # activity was either cancelled or workflow was completed or worker shut down
            # if you need to clean up you can catch this.
            # Here we are just reraising the exception
            raise
