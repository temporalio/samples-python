from temporalio import workflow

from message_passing.introduction import Language
from message_passing.introduction.workflows import (
    GetLanguagesInput,
    SetLanguageInput,
)

with workflow.unsafe.imports_passed_through():
    from nexus_sync_operations.service import GreetingService

NEXUS_ENDPOINT = "nexus-sync-operations-nexus-endpoint"


@workflow.defn
class CallerWorkflow:
    @workflow.run
    async def run(self) -> None:
        nexus_client = workflow.create_nexus_client(
            service=GreetingService,
            endpoint=NEXUS_ENDPOINT,
        )

        # Get supported languages
        supported_languages = await nexus_client.execute_operation(
            GreetingService.get_languages, GetLanguagesInput(include_unsupported=False)
        )
        print(f"supported languages: {supported_languages}")

        # Set language
        previous_language = await nexus_client.execute_operation(
            GreetingService.set_language,
            SetLanguageInput(language=Language.ARABIC),
        )
        assert (
            await nexus_client.execute_operation(GreetingService.get_language, None)
            == Language.ARABIC
        )
        print(f"language changed: {previous_language.name} -> {Language.ARABIC.name}")
