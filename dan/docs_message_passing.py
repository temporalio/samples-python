import asyncio
from dataclasses import dataclass
from enum import IntEnum
from typing import Optional

from temporalio import workflow


class Language(IntEnum):
    CHINESE = 1
    ENGLISH = 2
    FRENCH = 3
    SPANISH = 4
    PORTUGUESE = 5


@dataclass
class GetLanguagesInput:
    include_unsupported: bool


@dataclass
class ApproveInput:
    name: str


@workflow.defn
class GreetingWorkflow:
    def __init__(self) -> None:
        self.approved_for_release = False
        self.approver_name: Optional[str] = None
        self.language = Language.ENGLISH
        self.greetings = {
            Language.ENGLISH: "Hello, world",
            Language.CHINESE: "你好，世界",
        }

    @workflow.run
    async def run(self) -> str:
        await workflow.wait_condition(lambda: self.approved_for_release)
        return self.greetings[self.language]

    @workflow.query
    def get_languages(self, input: GetLanguagesInput) -> list[Language]:
        # 👉 A Query handler returns a value: it can inspect but must not mutate the Workflow state.
        if input.include_unsupported:
            return list(Language)
        else:
            return [lang for lang in Language if lang in self.greetings]

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


from temporalio.client import Client, WorkflowUpdateStage
from temporalio.worker import Worker


async def main():
    client = await Client.connect("localhost:7233")
    async with Worker(
        client,
        task_queue="my-task-queue",
        workflows=[GreetingWorkflow],
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
            GreetingWorkflow.set_language, Language.CHINESE
        )
        current_language = await wf_handle.query(GreetingWorkflow.get_language)
        print(f"language changed: {previous_language.name} -> {current_language.name}")

        update_handle = await wf_handle.start_update(
            GreetingWorkflow.set_language,
            Language.ENGLISH,
            wait_for_stage=WorkflowUpdateStage.ACCEPTED,
        )
        previous_language = await update_handle.result()
        current_language = await wf_handle.query(GreetingWorkflow.get_language)
        print(f"language changed: {previous_language.name} -> {current_language.name}")

        await wf_handle.signal(GreetingWorkflow.approve, ApproveInput(name=""))
        print(await wf_handle.result())


if __name__ == "__main__":
    asyncio.run(main())
