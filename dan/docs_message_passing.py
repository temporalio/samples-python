import asyncio
from enum import IntEnum
from typing import Optional

from temporalio import common, workflow
from temporalio.client import Client
from temporalio.worker import Worker

wid = __file__
tq = "tq"


class Language(IntEnum):
    Chinese = 1
    English = 2
    French = 3
    Spanish = 4
    Portuguese = 5


GREETINGS = {
    Language.English: "Hello, world!",
    Language.Chinese: "你好，世界!",
}


@workflow.defn
class GreetingWorkflow:
    def __init__(self) -> None:
        self.approved_for_release = False
        self.language = Language.English

    @workflow.run
    async def run(self) -> Optional[str]:
        await workflow.wait_condition(lambda: self.approved_for_release)
        return GREETINGS[self.language]

    @workflow.query
    def get_language(self) -> Language:
        return self.language

    @workflow.signal
    def approve(self) -> None:
        self.approved_for_release = True

    @workflow.update
    def set_language(self, language: Language) -> Language:
        previous_language, self.language = self.language, language
        return previous_language

    @set_language.validator
    def validate_language(self, language: Language) -> None:
        if language not in GREETINGS:
            raise ValueError(f"{language.name} is not supported")


async def main():
    client = await Client.connect("localhost:7233")
    async with Worker(
        client,
        task_queue=tq,
        workflows=[GreetingWorkflow],
    ):
        wf_handle = await client.start_workflow(
            GreetingWorkflow.run,
            id=wid,
            task_queue=tq,
            id_reuse_policy=common.WorkflowIDReusePolicy.TERMINATE_IF_RUNNING,
        )
        await wf_handle.execute_update(GreetingWorkflow.set_language, Language.Chinese)
        if False:
            await wf_handle.execute_update(
                GreetingWorkflow.set_language, Language.French
            )
        await wf_handle.signal(GreetingWorkflow.approve)
        print(await wf_handle.result())


if __name__ == "__main__":
    asyncio.run(main())
