import asyncio
from dataclasses import dataclass
from datetime import timedelta
from enum import IntEnum
from typing import Optional

from temporalio import activity, exceptions, workflow


class Language(IntEnum):
    Arabic = 1
    Chinese = 2
    English = 3
    French = 4
    Hindi = 5
    Spanish = 6


@activity.defn
async def call_greeting_service(to_language: Language) -> Optional[str]:
    greetings = {
        Language.Arabic: "مرحبا بالعالم",
        Language.Chinese: "你好，世界!",
        Language.English: "Hello, world!",
        Language.French: "Bonjour, monde!",
        Language.Hindi: "नमस्ते दुनिया!",
        Language.Spanish: "¡Hola mundo!",
    }
    await asyncio.sleep(0.2)  # Pretend to do a network call
    return greetings.get(to_language)


@dataclass
class GetLanguagesInput:
    supported_only: bool


@dataclass
class ApproveInput:
    name: str


@workflow.defn
class GreetingWorkflow:
    def __init__(self) -> None:
        self.approved_for_release = False
        self.approver_name: Optional[str] = None
        self.language = Language.English
        self.greetings = {
            Language.English: "Hello, world!",
            Language.Chinese: "你好，世界!",
        }
        self.lock = asyncio.Lock()

    @workflow.run
    async def run(self) -> str:
        await workflow.wait_condition(lambda: self.approved_for_release)
        await workflow.wait_condition(workflow.all_handlers_finished)
        return self.greetings[self.language]

    @workflow.query
    def get_language(self) -> Language:
        return self.language

    @workflow.query
    def get_languages(self, input: GetLanguagesInput) -> list[Language]:
        if input.supported_only:
            return [lang for lang in Language if lang in self.greetings]
        else:
            return list(Language)

    @workflow.signal
    def approve(self, input: ApproveInput) -> None:
        self.approved_for_release = True
        self.approver_name = input.name

    @workflow.update
    async def my_update(self, update_input: UpdateInput) -> str:
        await workflow.wait_condition(
            lambda: self.ready_for_update_to_execute(update_input)
        )
        return "update-result"

    @workflow.update
    async def set_language(self, language: Language) -> Language:
        if language not in self.greetings:
            greeting = await workflow.execute_activity(
                call_greeting_service,
                language,
                start_to_close_timeout=timedelta(seconds=10),
            )
            if greeting is None:
                # An update validator cannot be async, so cannot be used to check that the remote
                # call_greeting_service supports the requested language. Raising ApplicationError
                # will fail the Update, but the WorkflowExecutionUpdateAccepted event will still be
                # added to history.
                raise exceptions.ApplicationError(
                    f"Greeting service does not support {language.name}"
                )
            self.greetings[language] = greeting
        previous_language, self.language = self.language, language
        return previous_language

    @workflow.signal
    async def bad_async_handler(self):
        data = await workflow.execute_activity(
            fetch_data, start_to_close_timeout=timedelta(seconds=10)
        )
        self.x = data.x
        # 🐛🐛 Bug!! If multiple instances of this handler are executing concurrently, then
        # there may be times when the Workflow has self.x from one Activity execution and self.y from another.
        await asyncio.sleep(1)  # or await anything else
        self.y = data.y

    @workflow.signal
    async def safe_async_handler(self):
        async with self.lock:
            data = await workflow.execute_activity(
                fetch_data, start_to_close_timeout=timedelta(seconds=10)
            )
            self.x = data.x
            # The scheduler may switch to a different handler execution, or the main workflow
            # method, but no other execution of this handler can run until this execution finishes.
            await asyncio.sleep(1)  # or await anything else
            self.y = data.y


@dataclass
class Payload:
    x: float
    y: float


@activity.defn
async def fetch_data() -> Payload:
    return Payload(0.0, 0.0)


from temporalio.client import Client, WorkflowUpdateStage
from temporalio.worker import Worker


async def main():
    client = await Client.connect("localhost:7233")
    async with Worker(
        client,
        task_queue="my-task-queue",
        workflows=[GreetingWorkflow],
        activities=[call_greeting_service],
    ):
        wf_handle = await client.start_workflow(
            GreetingWorkflow.run,
            id="greeting-workflow-1234",
            task_queue="my-task-queue",
        )
        supported_languages = await wf_handle.query(
            GreetingWorkflow.get_languages, GetLanguagesInput(supported_only=True)
        )
        print(f"supported languages: {supported_languages}")

        previous_language = await wf_handle.execute_update(
            GreetingWorkflow.set_language, Language.Chinese
        )
        current_language = await wf_handle.query(GreetingWorkflow.get_language)
        print(f"language changed: {previous_language.name} -> {current_language.name}")

        # start_update
        update_handle = await wf_handle.start_update(
            GreetingWorkflow.set_language,
            Language.Arabic,
            wait_for_stage=WorkflowUpdateStage.ACCEPTED,
        )
        previous_language = await update_handle.result()
        current_language = await wf_handle.query(GreetingWorkflow.get_language)
        print(f"language changed: {previous_language.name} -> {current_language.name}")

        await wf_handle.signal(GreetingWorkflow.approve, ApproveInput(name=""))
        print(await wf_handle.result())


if __name__ == "__main__":
    asyncio.run(main())
