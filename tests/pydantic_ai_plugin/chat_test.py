import asyncio
import uuid

from temporalio.client import Client, WorkflowExecutionStatus
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from pydantic_ai.durable_exec.temporal import PydanticAIPlugin
from pydantic_ai_plugin.chat.workflow import ChatInput, ChatWorkflow


async def test_chat_carries_messages_across_continue_as_new() -> None:
    async with await WorkflowEnvironment.start_local(
        dev_server_extra_args=[
            "--dynamic-config-value",
            "limit.historyCount.suggestContinueAsNew=5",
        ]
    ) as env:
        config = env.client.config()
        config["plugins"] = [*config["plugins"], PydanticAIPlugin()]
        client = Client(**config)
        task_queue = f"pydantic-ai-chat-{uuid.uuid4()}"
        workflow_id = f"pydantic-ai-chat-{uuid.uuid4()}"

        async with Worker(
            client,
            task_queue=task_queue,
            workflows=[ChatWorkflow],
            max_cached_workflows=0,
        ):
            handle = await client.start_workflow(
                ChatWorkflow.run,
                ChatInput(),
                id=workflow_id,
                task_queue=task_queue,
            )
            first_run_id = handle.result_run_id
            assert await handle.execute_update(ChatWorkflow.turn, "Hello") == (
                "Ready for the next turn."
            )

            first_run = client.get_workflow_handle(workflow_id, run_id=first_run_id)
            for _ in range(100):
                if (
                    await first_run.describe()
                ).status == WorkflowExecutionStatus.CONTINUED_AS_NEW:
                    break
                await asyncio.sleep(0.1)
            else:
                raise AssertionError("workflow did not continue as new")

            latest = client.get_workflow_handle(workflow_id)
            assert await latest.execute_update(ChatWorkflow.turn, "Again") == (
                "Ready for the next turn."
            )
            assert await latest.query(ChatWorkflow.message_count) == 4
            await latest.signal(ChatWorkflow.end_chat)
            await latest.result()
