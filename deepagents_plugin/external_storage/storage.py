"""Retain each conversation message once, outside Temporal's payload storage."""

import asyncio
import json
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any

from botocore.exceptions import ClientError
from langchain_core.callbacks import (
    AsyncCallbackManagerForLLMRun,
    CallbackManagerForLLMRun,
)
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    SystemMessage,
    ToolMessage,
    messages_from_dict,
    messages_to_dict,
)
from langchain_core.outputs import ChatGeneration, ChatResult
from temporalio.deepagents.testing import FakeModel
from temporalio.exceptions import ApplicationError

if TYPE_CHECKING:
    from types_aiobotocore_s3.client import S3Client

CONTEXT_MESSAGES = 16


class TranscriptStore:
    def __init__(self, client: "S3Client", bucket: str) -> None:
        self.client = client
        self.bucket = bucket

    async def get(self, conversation_id: str, index: int) -> BaseMessage | None:
        try:
            response = await self.client.get_object(
                Bucket=self.bucket,
                Key=f"conversations/{conversation_id}/{index:08d}.json",
            )
        except ClientError as error:
            if error.response["Error"]["Code"] == "NoSuchKey":
                return None
            raise
        async with response["Body"] as body:
            return messages_from_dict([json.loads(await body.read())])[0]

    async def put(
        self, conversation_id: str, index: int, message: BaseMessage
    ) -> BaseMessage:
        try:
            await self.client.put_object(
                Bucket=self.bucket,
                Key=f"conversations/{conversation_id}/{index:08d}.json",
                Body=json.dumps(messages_to_dict([message])[0]).encode(),
                ContentType="application/json",
                IfNoneMatch="*",
            )
            return message
        except ClientError as error:
            if error.response["Error"]["Code"] != "PreconditionFailed":
                raise
        existing = await self.get(conversation_id, index)
        if existing is None:
            raise RuntimeError(
                "Transcript message disappeared after a conditional write"
            )
        return existing

    async def read(
        self, conversation_id: str, start: int, stop: int
    ) -> list[BaseMessage]:
        messages = await asyncio.gather(
            *[self.get(conversation_id, index) for index in range(start, stop)]
        )
        if any(message is None for message in messages):
            raise ApplicationError("Transcript message is missing", non_retryable=True)
        return [message for message in messages if message is not None]


class ConversationModel(BaseChatModel):
    """Worker-side wrapper; the plugin still runs every model call as an activity."""

    store: TranscriptStore

    @property
    def _llm_type(self) -> str:
        return "s3-conversation"

    def bind_tools(self, tools: Sequence[Any], **kwargs: Any) -> Any:
        # The demo scripts its tool call rather than asking a real provider.
        return self

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        raise NotImplementedError("Use the async model")

    async def _agenerate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: AsyncCallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        current = [m for m in messages if not isinstance(m, SystemMessage)]
        reference = current[0].additional_kwargs
        conversation_id = reference["conversation_id"]
        offset = reference["message_offset"]
        end = offset + len(current)
        for index, message in enumerate(current, offset):
            existing = await self.store.put(conversation_id, index, message)
            # LangGraph can regenerate message IDs on replay; S3 positions are
            # the stable identity. Tool call IDs remain part of the comparison.
            if existing.model_dump(exclude={"id"}) != message.model_dump(
                exclude={"id"}
            ):
                raise ApplicationError(
                    "Conflicting transcript message", non_retryable=True
                )
        reply = await self.store.get(conversation_id, end)
        if reply is None:
            recent = await self.store.read(
                conversation_id, max(0, end - CONTEXT_MESSAGES), end
            )
            # Drop leading tool results if their calls fell outside the window.
            while recent and isinstance(recent[0], ToolMessage):
                recent.pop(0)
            context = [m for m in messages if isinstance(m, SystemMessage)] + recent
            response = await FakeModel([scripted_reply(recent)]).ainvoke(context)
            # Conditional writes make committed replies reusable after retries.
            reply = await self.store.put(conversation_id, end, response)
        return ChatResult(generations=[ChatGeneration(message=reply)])


def scripted_reply(messages: list[BaseMessage]) -> AIMessage:
    latest = messages[-1]
    if isinstance(latest, ToolMessage):
        return AIMessage(content="I received the complete document.")
    if str(latest.content).startswith("Read large-document.txt"):
        return AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "read_file",
                    "args": {"file_path": "large-document.txt"},
                    "id": "call-read",
                }
            ],
        )
    replies = {
        "I am working on a project called Cedar.": "The project is called Cedar.",
        "The project uses Python.": "Cedar uses Python.",
        "It is due Friday.": "Cedar is due Friday.",
    }
    if str(latest.content).startswith("Remind me"):
        context = "\n".join(str(message.content) for message in messages)
        return AIMessage(
            content=(
                "Cedar is a Python project due Friday."
                if all(fact in context for fact in ("Cedar", "Python", "Friday"))
                else "Those details are outside my recent context."
            )
        )
    return AIMessage(content=replies.get(str(latest.content), "Acknowledged."))
