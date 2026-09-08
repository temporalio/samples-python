"""
A long-running "entity" workflow that backs the NexusRemoteGreetingService Nexus
operations. The workflow exposes queries, an update, and a signal. These are private
implementation details of the Nexus service: the caller only interacts via Nexus
operations.
"""

import asyncio
from datetime import timedelta
from typing import Optional

from temporalio import workflow
from temporalio.exceptions import ApplicationError

from nexus_messaging.ondemandpattern.handler.activities import call_greeting_service
from nexus_messaging.ondemandpattern.service import (
    ApproveInput,
    AttachApprovalContextInput,
    GetLanguagesInput,
    GetLanguagesOutput,
    Language,
    SetLanguageInput,
)

ATTACH_APPROVAL_CONTEXT_SIGNAL = "attach_approval_context"


@workflow.defn
class GreetingWorkflow:
    def __init__(self) -> None:
        self.approved_for_release = False
        self.greetings: dict[Language, str] = {
            Language.CHINESE: "\u4f60\u597d\uff0c\u4e16\u754c",
            Language.ENGLISH: "Hello, world",
        }
        self.language = Language.ENGLISH
        self.approval_context: Optional[str] = None
        self.lock = asyncio.Lock()

    @workflow.run
    async def run(self) -> str:
        # Wait until approved and all in-flight update handlers have finished.
        await workflow.wait_condition(
            lambda: self.approved_for_release and workflow.all_handlers_finished()
        )
        return self.greetings[self.language]

    @workflow.query
    def get_languages(self, input: GetLanguagesInput) -> GetLanguagesOutput:
        if input.include_unsupported:
            languages = sorted(Language)
        else:
            languages = sorted(self.greetings)
        return GetLanguagesOutput(languages=languages)

    @workflow.query
    def get_language(self) -> Language:
        return self.language

    @workflow.signal
    def approve(self, input: ApproveInput) -> None:
        workflow.logger.info(
            "Approval signal received for user %s (context: %s)",
            input.user_id,
            self.approval_context,
        )
        self.approved_for_release = True

    # Attaches supporting information for the eventual approval. Delivered with
    # Signal-with-Start, so this may be the message that creates the workflow.
    @workflow.signal(name=ATTACH_APPROVAL_CONTEXT_SIGNAL)
    def attach_approval_context(self, input: AttachApprovalContextInput) -> None:
        workflow.logger.info(
            "attach_approval_context signal received for user %s: %s",
            input.user_id,
            input.note,
        )
        self.approval_context = input.note

    @workflow.update
    def set_language(self, input: SetLanguageInput) -> Language:
        workflow.logger.info("setLanguage update received for user %s", input.user_id)
        previous_language, self.language = self.language, input.language
        return previous_language

    @set_language.validator
    def validate_set_language(self, input: SetLanguageInput) -> None:
        if input.language not in self.greetings:
            raise ValueError(f"{input.language.name} is not supported")

    # Changes the active language, calling an activity to fetch a greeting for new
    # languages not already in the greetings map.
    @workflow.update
    async def set_language_using_activity(self, input: SetLanguageInput) -> Language:
        if input.language not in self.greetings:
            async with self.lock:
                greeting = await workflow.execute_activity(
                    call_greeting_service,
                    input.language,
                    start_to_close_timeout=timedelta(seconds=10),
                )
                if greeting is None:
                    raise ApplicationError(
                        f"Greeting service does not support {input.language.name}"
                    )
                self.greetings[input.language] = greeting
        previous_language, self.language = self.language, input.language
        return previous_language
