import asyncio
from typing import Optional

from temporalio.client import Client, WorkflowUpdateStage

from message_passing.introduction import TASK_QUEUE
from message_passing.introduction.workflows import (
    ApproveInput,
    GetLanguagesInput,
    GreetingWorkflow,
    Language,
)


async def main(client: Optional[Client] = None):
    client = client or await Client.connect("localhost:7233")
    wf_handle = await client.start_workflow(
        GreetingWorkflow.run,
        id="greeting-workflow-1234",
        task_queue=TASK_QUEUE,
    )

    # 👉 Send a Query
    supported_languages = await wf_handle.query(
        GreetingWorkflow.get_languages, GetLanguagesInput(include_unsupported=False)
    )
    print(f"supported languages: {supported_languages}")

    # 👉 Execute an Update
    previous_language = await wf_handle.execute_update(
        GreetingWorkflow.set_language, Language.CHINESE
    )
    current_language = await wf_handle.query(GreetingWorkflow.get_language)
    print(f"language changed: {previous_language.name} -> {current_language.name}")

    # 👉 Start an Update and then wait for it to complete
    update_handle = await wf_handle.start_update(
        GreetingWorkflow.set_language_using_activity,
        Language.ARABIC,
        wait_for_stage=WorkflowUpdateStage.ACCEPTED,
    )
    previous_language = await update_handle.result()
    current_language = await wf_handle.query(GreetingWorkflow.get_language)
    print(f"language changed: {previous_language.name} -> {current_language.name}")

    # 👉 Send a Signal
    await wf_handle.signal(GreetingWorkflow.approve, ApproveInput(name=""))
    print(await wf_handle.result())


if __name__ == "__main__":
    asyncio.run(main())
