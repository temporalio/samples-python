"""Exercise native External Storage with a large tool result and a conversation."""

from dataclasses import dataclass
from datetime import timedelta

from langchain_core.messages import HumanMessage, ToolMessage
from langchain_core.tools import tool
from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.deepagents import create_temporal_deep_agent, tool_as_activity

PAYLOAD_BYTES = 6 * 1024 * 1024
TASK_QUEUE = "deepagents-external-storage"


@dataclass
class ExternalStorageResult:
    tool_result_bytes: int
    turns: int
    last_answer: str
    conversation_id: str
    message_count: int


@tool
async def read_file(file_path: str) -> str:
    """Read a mock document containing exactly 6 MiB of text."""
    del file_path
    return "x" * PAYLOAD_BYTES


@workflow.defn
class ExternalStorageAgent:
    @workflow.run
    async def run(self, questions: list[str]) -> ExternalStorageResult:
        reader = tool_as_activity(
            read_file,
            start_to_close_timeout=timedelta(seconds=30),
            activity_options={"retry_policy": RetryPolicy(maximum_attempts=1)},
        )
        conversation_id = workflow.info().run_id
        message_count = 0
        tool_result_bytes = 0
        last_answer = ""
        agent = create_temporal_deep_agent(
            model="fake:conversation",
            tools=[reader],
            system_prompt=(
                "Answer using the recent conversation. For the first request, "
                "read the document and acknowledge receiving it."
            ),
            activity_options={"start_to_close_timeout": timedelta(seconds=30)},
        )

        for index, question in enumerate(questions):
            result = await agent.ainvoke(
                {
                    "messages": [
                        HumanMessage(
                            content=question,
                            additional_kwargs={
                                "conversation_id": conversation_id,
                                "message_offset": message_count,
                            },
                        )
                    ]
                }
            )
            if index == 0:
                message = next(
                    message
                    for message in result["messages"]
                    if isinstance(message, ToolMessage) and message.name == "read_file"
                )
                if not isinstance(message.content, str):
                    raise TypeError("Expected the document tool result to be text")
                tool_result_bytes = len(message.content.encode())

            answer = result["messages"][-1].content
            if not isinstance(answer, str):
                raise TypeError("Expected a text response from the model")
            message_count += len(result["messages"])
            last_answer = answer

        if not questions:
            raise ValueError("At least one question is required")
        return ExternalStorageResult(
            tool_result_bytes=tool_result_bytes,
            turns=len(questions),
            last_answer=last_answer,
            conversation_id=conversation_id,
            message_count=message_count,
        )
