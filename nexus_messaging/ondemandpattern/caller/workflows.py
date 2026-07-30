"""
A caller workflow that creates and controls workflow instances through Nexus operations.
Unlike the entity (callerpattern), no workflow is pre-started; the caller creates them
on demand via the run_from_remote operation.
"""

from temporalio import workflow

from nexus_messaging.ondemandpattern.service import (
    ApproveInput,
    GetLanguageInput,
    GetLanguagesInput,
    Language,
    NexusRemoteGreetingService,
    RunFromRemoteInput,
    SetLanguageInput,
)

NEXUS_ENDPOINT = "nexus-messaging-nexus-endpoint"

REMOTE_WORKFLOW_ONE = "UserId One"
REMOTE_WORKFLOW_TWO = "UserId Two"


@workflow.defn
class CallerRemoteWorkflow:
    def __init__(self) -> None:
        self.nexus_client = workflow.create_nexus_client(
            service=NexusRemoteGreetingService,
            endpoint=NEXUS_ENDPOINT,
        )

    @workflow.run
    async def run(self) -> list[str]:
        log: list[str] = []

        # Each call is performed twice in this example. This assumes there are two
        # users we want to process. The first calls start two workflows, one for each
        # user. Subsequent calls perform different actions between the two users.

        # This is an async Nexus operation -- starts a workflow on the handler and
        # returns a handle. Unlike the sync operations below, this does not block
        # until the workflow completes. It is backed by workflow_run_operation on the
        # handler side.
        handle_one = await self.nexus_client.start_operation(
            NexusRemoteGreetingService.run_from_remote,
            RunFromRemoteInput(user_id=REMOTE_WORKFLOW_ONE),
        )
        log.append(f"started remote greeting workflow: {REMOTE_WORKFLOW_ONE}")
        workflow.logger.info("started remote greeting workflow %s", REMOTE_WORKFLOW_ONE)

        handle_two = await self.nexus_client.start_operation(
            NexusRemoteGreetingService.run_from_remote,
            RunFromRemoteInput(user_id=REMOTE_WORKFLOW_TWO),
        )
        log.append(f"started remote greeting workflow: {REMOTE_WORKFLOW_TWO}")
        workflow.logger.info("started remote greeting workflow %s", REMOTE_WORKFLOW_TWO)

        # Query the remote workflows for supported languages.
        languages_output = await self.nexus_client.execute_operation(
            NexusRemoteGreetingService.get_languages,
            GetLanguagesInput(include_unsupported=False, user_id=REMOTE_WORKFLOW_ONE),
        )
        log.append(
            f"Supported languages for {REMOTE_WORKFLOW_ONE}: "
            f"{languages_output.languages}"
        )
        workflow.logger.info(
            "supported languages are %s for workflow %s",
            languages_output.languages,
            REMOTE_WORKFLOW_ONE,
        )

        languages_output = await self.nexus_client.execute_operation(
            NexusRemoteGreetingService.get_languages,
            GetLanguagesInput(include_unsupported=False, user_id=REMOTE_WORKFLOW_TWO),
        )
        log.append(
            f"Supported languages for {REMOTE_WORKFLOW_TWO}: "
            f"{languages_output.languages}"
        )
        workflow.logger.info(
            "supported languages are %s for workflow %s",
            languages_output.languages,
            REMOTE_WORKFLOW_TWO,
        )

        # Update the language on each remote workflow.
        previous_language_one = await self.nexus_client.execute_operation(
            NexusRemoteGreetingService.set_language,
            SetLanguageInput(language=Language.ARABIC, user_id=REMOTE_WORKFLOW_ONE),
        )

        previous_language_two = await self.nexus_client.execute_operation(
            NexusRemoteGreetingService.set_language,
            SetLanguageInput(language=Language.HINDI, user_id=REMOTE_WORKFLOW_TWO),
        )

        # Confirm the changes by querying.
        current_language = await self.nexus_client.execute_operation(
            NexusRemoteGreetingService.get_language,
            GetLanguageInput(user_id=REMOTE_WORKFLOW_ONE),
        )
        log.append(
            f"{REMOTE_WORKFLOW_ONE} changed language: "
            f"{previous_language_one.name} -> {current_language.name}"
        )
        workflow.logger.info(
            "Language changed from %s to %s for workflow %s",
            previous_language_one,
            current_language,
            REMOTE_WORKFLOW_ONE,
        )

        current_language = await self.nexus_client.execute_operation(
            NexusRemoteGreetingService.get_language,
            GetLanguageInput(user_id=REMOTE_WORKFLOW_TWO),
        )
        log.append(
            f"{REMOTE_WORKFLOW_TWO} changed language: "
            f"{previous_language_two.name} -> {current_language.name}"
        )
        workflow.logger.info(
            "Language changed from %s to %s for workflow %s",
            previous_language_two,
            current_language,
            REMOTE_WORKFLOW_TWO,
        )

        # Approve both workflows so they can complete.
        await self.nexus_client.execute_operation(
            NexusRemoteGreetingService.approve,
            ApproveInput(name="remote-caller", user_id=REMOTE_WORKFLOW_ONE),
        )
        await self.nexus_client.execute_operation(
            NexusRemoteGreetingService.approve,
            ApproveInput(name="remote-caller", user_id=REMOTE_WORKFLOW_TWO),
        )
        log.append("Workflows approved")

        # Wait for the remote workflows to finish and return their results.
        result = await handle_one
        log.append(f"Workflow one result: {result}")

        result = await handle_two
        log.append(f"Workflow two result: {result}")

        return log
