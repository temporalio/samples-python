"""
A caller workflow that executes Nexus operations. The caller does not have information
about how these operations are implemented by the Nexus service.
"""

from temporalio import workflow
from temporalio.exceptions import ApplicationError

from nexus_messaging.callerpattern.service import (
    ApproveInput,
    GetLanguageInput,
    GetLanguagesInput,
    Language,
    NexusGreetingService,
    SetLanguageInput,
)

NEXUS_ENDPOINT = "nexus-messaging-nexus-endpoint"


@workflow.defn
class CallerWorkflow:
    @workflow.run
    async def run(self, user_id: str) -> list[str]:
        log: list[str] = []
        nexus_client = workflow.create_nexus_client(
            service=NexusGreetingService,
            endpoint=NEXUS_ENDPOINT,
        )

        # Call a Nexus operation backed by a query against the entity workflow.
        # The workflow must already be running on the handler, otherwise you will
        # get an error saying the workflow has already terminated.
        languages_output = await nexus_client.execute_operation(
            NexusGreetingService.get_languages,
            GetLanguagesInput(include_unsupported=False, user_id=user_id),
        )
        log.append(f"Supported languages: {languages_output.languages}")
        workflow.logger.info("Supported languages: %s", languages_output.languages)

        # Following are examples for each of the three messaging types -
        # update, query, then signal.

        # Call a Nexus operation backed by an update against the entity workflow.
        previous_language = await nexus_client.execute_operation(
            NexusGreetingService.set_language,
            SetLanguageInput(language=Language.ARABIC, user_id=user_id),
        )

        # Call a Nexus operation backed by a query to confirm the language change.
        current_language = await nexus_client.execute_operation(
            NexusGreetingService.get_language,
            GetLanguageInput(user_id=user_id),
        )
        if current_language != Language.ARABIC:
            raise ApplicationError(f"Expected language ARABIC, got {current_language}")

        log.append(
            f"Language changed: {previous_language.name} -> {Language.ARABIC.name}"
        )
        workflow.logger.info(
            "Language changed from %s to %s", previous_language, Language.ARABIC
        )

        # Call a Nexus operation backed by a signal against the entity workflow.
        await nexus_client.execute_operation(
            NexusGreetingService.approve,
            ApproveInput(name="caller", user_id=user_id),
        )
        log.append("Workflow approved")
        workflow.logger.info("Workflow approved")

        return log
