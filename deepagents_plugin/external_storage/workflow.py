"""A Deep Agent whose tool returns 6 MiB, carried by native External Storage."""

import hashlib
from dataclasses import dataclass
from datetime import timedelta

from langchain_core.messages import ToolMessage
from langchain_core.tools import tool
from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.deepagents import (
    create_temporal_deep_agent,
    tool_as_activity,
)

PAYLOAD_BYTES = 6 * 1024 * 1024
MODEL = "fake:external-storage"
TASK_QUEUE = "deepagents-external-storage"


@dataclass
class AgentResult:
    """Small integrity evidence; the large document stays out of the final result."""

    result_bytes: int
    sha256: str
    answer: str


@tool
async def read_file(file_path: str) -> str:
    """Read a mock document containing exactly 6 MiB of text."""
    # Override the built-in read_file with an activity-backed bulk reader.
    # Deep Agents excludes read_file from tool-result eviction, so its complete
    # content reaches the next model activity. Real file I/O would go here.
    del file_path
    return "x" * PAYLOAD_BYTES


# @@@SNIPSTART python-deepagents-external-storage-workflow
@workflow.defn
class ExternalStorageAgent:
    @workflow.run
    async def run(self, question: str) -> AgentResult:
        reader = tool_as_activity(
            read_file,
            start_to_close_timeout=timedelta(seconds=30),
            activity_options={"retry_policy": RetryPolicy(maximum_attempts=1)},
        )
        agent = create_temporal_deep_agent(
            model=MODEL,
            tools=[reader],
            system_prompt="Read the document, then acknowledge receiving the result.",
            activity_options={"start_to_close_timeout": timedelta(seconds=30)},
        )
        result = await agent.ainvoke(
            {"messages": [{"role": "user", "content": question}]}
        )
        tool_result = next(
            message
            for message in result["messages"]
            if isinstance(message, ToolMessage) and message.name == "read_file"
        )
        assert isinstance(tool_result.content, str)
        data = tool_result.content.encode()
        answer = result["messages"][-1].content
        assert isinstance(answer, str)
        return AgentResult(
            result_bytes=len(data),
            sha256=hashlib.sha256(data).hexdigest(),
            answer=answer,
        )


# @@@SNIPEND
