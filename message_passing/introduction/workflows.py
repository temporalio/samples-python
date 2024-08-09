import asyncio
from dataclasses import dataclass
from datetime import timedelta
from enum import IntEnum
from typing import Optional

from temporalio import activity, workflow
from temporalio.exceptions import ApplicationError


class Language(IntEnum):
    ARABIC = 1
    CHINESE = 2
    ENGLISH = 3
    FRENCH = 4
    HINDI = 5
    PORTUGUESE = 6
    SPANISH = 7


@dataclass
class GetLanguagesInput:
    include_unsupported: bool


@dataclass
class ApproveInput:
    name: str


@workflow.defn
class GreetingWorkflow:
    """
    A workflow that that returns a greeting in one of two languages.

    It supports a Query to obtain the current language, an Update to change the
    current language and receive the previous language in response, and a Signal
    to approve the Workflow so that it is allowed to return its result.
    """

    # 👉 This Workflow does not use any async handlers and so cannot use any
    # Activities. It only supports two languages, whose greetings are hardcoded
    # in the Workflow definition. See GreetingWorkflowWithAsyncHandler below for
    # a Workflow that uses an async Update handler to call an Activity.

    def __init__(self) -> None:
        self.approved_for_release = False
        self.approver_name: Optional[str] = None
        self.greetings = {
            Language.CHINESE: "你好，世界",
            Language.ENGLISH: "Hello, world",
        }
        self.language = Language.ENGLISH

    @workflow.run
    async def run(self) -> str:
        await workflow.wait_condition(lambda: self.approved_for_release)
        return self.greetings[self.language]

    @workflow.query
    def get_languages(self, input: GetLanguagesInput) -> list[Language]:
        # 👉 A Query handler returns a value: it can inspect but must not mutate the Workflow state.
        if input.include_unsupported:
            return sorted(Language)
        else:
            return sorted(self.greetings)

    @workflow.signal
    def approve(self, input: ApproveInput) -> None:
        # 👉 A Signal handler mutates the Workflow state but cannot return a value.
        self.approved_for_release = True
        self.approver_name = input.name

    @workflow.update
    def set_language(self, language: Language) -> Language:
        # 👉 An Update handler can mutate the Workflow state and return a value.
        previous_language, self.language = self.language, language
        return previous_language

    @set_language.validator
    def validate_language(self, language: Language) -> None:
        if language not in self.greetings:
            # 👉 In an Update validator you raise any exception to reject the Update.
            raise ValueError(f"{language.name} is not supported")

    @workflow.query
    def get_language(self) -> Language:
        return self.language


@workflow.defn
class GreetingWorkflowWithAsyncHandler(GreetingWorkflow):
    """
    A workflow that that returns a greeting in one of many available languages.

    It supports a Query to obtain the current language, an Update to change the
    current language and receive the previous language in response, and a Signal
    to approve the Workflow so that it is allowed to return its result.
    """

    # 👉 This workflow supports the full range of languages, because the update
    # handler is async and uses an activity to call a remote service.

    def __init__(self) -> None:
        super().__init__()
        self.lock = asyncio.Lock()

    @workflow.run
    async def run(self) -> str:
        # 👉 In addition to waiting for the `approve` Signal, we also wait for
        # all handlers to finish. Otherwise, the Workflow might return its
        # result while a set_language Update is in progress.
        await workflow.wait_condition(
            lambda: self.approved_for_release and workflow.all_handlers_finished()
        )
        return self.greetings[self.language]

    @workflow.update
    async def set_language(self, language: Language) -> Language:
        # 👉 An Update handler can mutate the Workflow state and return a value.
        # 👉 Since this update handler is async, it can execute an activity.
        if language not in self.greetings:
            # 👉 We use a lock so that, if this handler is executed multiple
            # times, each execution can schedule the activity only when the
            # previously scheduled activity has completed. This ensures that
            # multiple calls to set_language are processed in order.
            async with self.lock:
                greeting = await workflow.execute_activity(
                    call_greeting_service,
                    language,
                    start_to_close_timeout=timedelta(seconds=10),
                )
                if greeting is None:
                    # 👉 An update validator cannot be async, so cannot be used
                    # to check that the remote call_greeting_service supports
                    # the requested language. Raising ApplicationError will fail
                    # the Update, but the WorkflowExecutionUpdateAccepted event
                    # will still be added to history.
                    raise ApplicationError(
                        f"Greeting service does not support {language.name}"
                    )
                self.greetings[language] = greeting
        previous_language, self.language = self.language, language
        return previous_language


@activity.defn
async def call_greeting_service(to_language: Language) -> Optional[str]:
    greetings = {
        Language.ARABIC: "مرحبا بالعالم",
        Language.CHINESE: "你好，世界",
        Language.ENGLISH: "Hello, world",
        Language.FRENCH: "Bonjour, monde",
        Language.HINDI: "नमस्ते दुनिया",
        Language.PORTUGUESE: "Olá mundo",
        Language.SPANISH: "¡Hola mundo",
    }
    await asyncio.sleep(0.2)  # Simulate a network call
    return greetings.get(to_language)
