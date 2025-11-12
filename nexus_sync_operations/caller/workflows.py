"""
This is a workflow that calls nexus operations. The caller does not have information about how these
operations are implemented by the nexus service.
"""

from temporalio import workflow

from message_passing.introduction import Language
from message_passing.introduction.workflows import (
    ApproveInput,
    GetLanguagesInput,
    SetLanguageInput,
)

with workflow.unsafe.imports_passed_through():
    from nexus_sync_operations.service import GreetingService

NEXUS_ENDPOINT = "nexus-sync-operations-nexus-endpoint"


@workflow.defn
class CallerWorkflow:
    @workflow.run
    async def run(self) -> list[str]:
        log = []
        nexus_client = workflow.create_nexus_client(
            service=GreetingService,
            endpoint=NEXUS_ENDPOINT,
        )

        # 👉 QUERY OPERATION: Get supported languages
        supported_languages = await nexus_client.execute_operation(
            GreetingService.get_languages, GetLanguagesInput(include_unsupported=False)
        )
        log.append(f"Query - supported languages: {supported_languages}")

        # 👉 QUERY OPERATION: Get current language
        current_language = await nexus_client.execute_operation(
            GreetingService.get_language, None
        )
        log.append(f"Query - current language: {current_language.name}")

        # 👉 UPDATE OPERATION: Set language using synchronous update (non-async)
        previous_language = await nexus_client.execute_operation(
            GreetingService.set_language_sync,
            SetLanguageInput(language=Language.CHINESE),
        )
        assert (
            await nexus_client.execute_operation(GreetingService.get_language, None)
            == Language.CHINESE
        )
        log.append(
            f"Update (sync) - language changed: {previous_language.name} -> {Language.CHINESE.name}"
        )

        # 👉 UPDATE OPERATION: Set language using async update (with activity)
        previous_language = await nexus_client.execute_operation(
            GreetingService.set_language,
            SetLanguageInput(language=Language.ARABIC),
        )
        assert (
            await nexus_client.execute_operation(GreetingService.get_language, None)
            == Language.ARABIC
        )
        log.append(
            f"Update (async) - language changed: {previous_language.name} -> {Language.ARABIC.name}"
        )

        # 👉 SIGNAL OPERATION: Send approval signal
        await nexus_client.execute_operation(
            GreetingService.approve,
            ApproveInput(name="CallerWorkflow"),
        )
        log.append("Signal - approval sent")

        # 👉 SIGNAL-WITH-START OPERATION: Send approval signal, starting workflow if needed
        # This demonstrates signal-with-start, which will start the workflow if it doesn't exist
        await nexus_client.execute_operation(
            GreetingService.approve_with_start,
            ApproveInput(name="CallerWorkflow-SignalWithStart"),
        )
        log.append("Signal-with-start - approval sent (workflow started if needed)")

        return log
