"""Exercise native External Storage with a large tool result and a conversation."""

import hashlib
from dataclasses import dataclass
from datetime import timedelta

from langchain_core.messages import ToolMessage
from langchain_core.tools import tool
from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.deepagents import create_temporal_deep_agent, tool_as_activity

PAYLOAD_BYTES = 6 * 1024 * 1024
MODEL = "fake:external-storage"
TASK_QUEUE = "deepagents-external-storage"


@dataclass
class ConversationTurn:
    user: str
    assistant: str


@dataclass
class ExternalStorageResult:
    tool_result_bytes: int
    tool_result_sha256: str
    turns: int
    last_answer: str


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
        turns: list[ConversationTurn] = []
        tool_result: str | None = None
        last_answer = ""

        for index, question in enumerate(questions):
            history = "\n".join(
                f"User: {turn.user}\nAssistant: {turn.assistant}" for turn in turns
            )
            system_prompt = (
                "Answer the latest message using the conversation history. "
                "For the first request, read the requested document and acknowledge "
                "receiving it.\n\n"
                f"Conversation history:\n{history or '(no earlier turns)'}"
            )
            agent = create_temporal_deep_agent(
                model=MODEL,
                tools=[reader] if index == 0 else [],
                system_prompt=system_prompt,
                activity_options={"start_to_close_timeout": timedelta(seconds=30)},
            )
            result = await agent.ainvoke(
                {"messages": [{"role": "user", "content": question}]}
            )
            if index == 0:
                message = next(
                    message
                    for message in result["messages"]
                    if isinstance(message, ToolMessage) and message.name == "read_file"
                )
                if not isinstance(message.content, str):
                    raise TypeError("Expected the document tool result to be text")
                tool_result = message.content

            answer = result["messages"][-1].content
            if not isinstance(answer, str):
                raise TypeError("Expected a text response from the model")
            turns.append(ConversationTurn(user=question, assistant=answer))
            last_answer = answer

        if tool_result is None:
            raise ValueError("At least one question is required")
        tool_bytes = tool_result.encode()
        return ExternalStorageResult(
            tool_result_bytes=len(tool_bytes),
            tool_result_sha256=hashlib.sha256(tool_bytes).hexdigest(),
            turns=len(turns),
            last_answer=last_answer,
        )
