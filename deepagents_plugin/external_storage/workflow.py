"""Exercise native External Storage with a 6 MiB tool result."""

import hashlib
from dataclasses import dataclass
from datetime import timedelta

from langchain_core.messages import ToolMessage
from temporalio import workflow
from temporalio.deepagents import create_temporal_deep_agent

with workflow.unsafe.imports_passed_through():
    from deepagents_plugin.external_storage.tools import PAYLOAD_BYTES, reader


@dataclass
class ExternalStorageResult:
    tool_result_bytes: int
    tool_result_sha256: str
    last_answer: str


@workflow.defn
class ExternalStorageAgent:
    @workflow.run
    async def run(self, question: str) -> ExternalStorageResult:
        agent = create_temporal_deep_agent(
            model="fake:external-storage",
            tools=[reader],
            system_prompt="Read the requested document and acknowledge receiving it.",
            activity_options={"start_to_close_timeout": timedelta(seconds=30)},
        )

        result = await agent.ainvoke(
            {"messages": [{"role": "user", "content": question}]}
        )
        message = next(
            message
            for message in result["messages"]
            if isinstance(message, ToolMessage) and message.name == "read_file"
        )
        if not isinstance(message.content, str):
            raise TypeError("Expected the document tool result to be text")
        answer = result["messages"][-1].content
        if not isinstance(answer, str):
            raise TypeError("Expected a text response from the model")
        tool_bytes = message.content.encode()
        return ExternalStorageResult(
            tool_result_bytes=len(tool_bytes),
            tool_result_sha256=hashlib.sha256(tool_bytes).hexdigest(),
            last_answer=answer,
        )
