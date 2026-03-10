"""
Handler workflow started by the hello Nexus operation.

Demonstrates how to handle cancellation from the caller workflow using a
detached cancellation scope (asyncio.shield) for cleanup work.
"""

import asyncio

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from nexus_cancel.service import HelloInput, HelloOutput, Language

GREETINGS = {
    Language.EN: "Hello {name} 👋",
    Language.FR: "Bonjour {name} 👋",
    Language.DE: "Hallo {name} 👋",
    Language.ES: "¡Hola! {name} 👋",
    Language.TR: "Merhaba {name} 👋",
}


@workflow.defn
class HelloHandlerWorkflow:
    @workflow.run
    async def run(self, input: HelloInput) -> HelloOutput:
        try:
            # Sleep for a random duration to simulate work (0-5 seconds)
            random_seconds = workflow.random().randint(0, 5)
            workflow.logger.info(f"Working for {random_seconds} seconds...")
            await asyncio.sleep(random_seconds)

            # Return a greeting based on the language
            greeting = GREETINGS[input.language].format(name=input.name)
            return HelloOutput(message=greeting)

        except asyncio.CancelledError:
            # Perform cleanup in a detached cancellation scope.
            # asyncio.shield prevents the cleanup work from being cancelled.
            workflow.logger.info("Received cancellation request, performing cleanup...")
            try:
                cleanup_seconds = workflow.random().randint(0, 5)
                await asyncio.shield(asyncio.sleep(cleanup_seconds))
            except asyncio.CancelledError:
                pass
            workflow.logger.info("HelloHandlerWorkflow was cancelled successfully.")
            # Re-raise the cancellation error
            raise
