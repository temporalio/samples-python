"""Scripted streaming model for openai_agents sample tests.

Each entry in the script drives one ``stream_response`` call — that is, one
model activity: a ``str`` streams that text as deltas followed by a terminal
``ResponseCompletedEvent``, a :class:`ToolCall` emits a function call so the
agent runs the tool and comes back for another turn, and a
:class:`FailMidStream` cuts a response short so the activity is retried.

The plugin takes a ``model_provider`` directly, so nothing needs patching.
"""

from __future__ import annotations

import itertools
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any, Union

from agents import (
    AgentOutputSchemaBase,
    Handoff,
    Model,
    ModelProvider,
    ModelResponse,
    ModelSettings,
    ModelTracing,
    Tool,
    TResponseInputItem,
)
from agents.items import TResponseStreamEvent
from openai.types.responses import (
    Response,
    ResponseCompletedEvent,
    ResponseFunctionToolCall,
    ResponseOutputMessage,
    ResponseOutputText,
    ResponseTextDeltaEvent,
)

# Chunk size for text deltas. Small enough that any test text streams as
# several events, so a subscriber that reassembles them is doing real work.
_DELTA_CHARS = 12


@dataclass
class ToolCall:
    """Script entry for a turn that calls a tool instead of answering."""

    name: str
    arguments: str = "{}"


@dataclass
class FailMidStream:
    """Script entry that streams a few deltas and then raises.

    Simulates a model activity that dies partway through a response. The
    deltas it published are already on the workflow's stream, and because
    entries are consumed one per ``stream_response`` call, the activity's
    retry advances to the next script entry — normally the same text in
    full, as a real retry would re-sample the whole response.
    """

    text: str
    after_deltas: int = 4


# One script entry per stream_response call.
ScriptEntry = Union[str, ToolCall, FailMidStream]


def _message(text: str) -> ResponseOutputMessage:
    return ResponseOutputMessage(
        id="msg_mock",
        content=[ResponseOutputText(text=text, annotations=[], type="output_text")],
        role="assistant",
        status="completed",
        type="message",
    )


def _response(output: list[Any]) -> Response:
    return Response(
        id="resp_mock",
        created_at=0.0,
        model="mock-model",
        object="response",
        output=output,
        parallel_tool_calls=False,
        tool_choice="auto",
        tools=[],
        status="completed",
    )


class ScriptedStreamingModel(Model):
    """Model that replays a fixed script of turns, one per streamed call."""

    def __init__(self, script: list[ScriptEntry]) -> None:
        self._script = list(script)
        self._calls = itertools.count()

    def _next_turn(self) -> ScriptEntry:
        if not self._script:
            raise AssertionError("ScriptedStreamingModel script exhausted")
        return self._script.pop(0)

    async def get_response(self, *args: Any, **kwargs: Any) -> ModelResponse:
        """Unimplemented: this mock exists for Runner.run_streamed."""
        raise NotImplementedError

    async def stream_response(
        self,
        system_instructions: str | None,
        input: str | list[TResponseInputItem],
        model_settings: ModelSettings,
        tools: list[Tool],
        output_schema: AgentOutputSchemaBase | None,
        handoffs: list[Handoff],
        tracing: ModelTracing,
        **kwargs: Any,
    ) -> AsyncIterator[TResponseStreamEvent]:
        turn = self._next_turn()
        seq = itertools.count()

        if isinstance(turn, ToolCall):
            call = self._tool_call(turn, next(self._calls))
            yield ResponseCompletedEvent(
                response=_response([call]),
                sequence_number=next(seq),
                type="response.completed",
            )
            return

        text = turn.text if isinstance(turn, FailMidStream) else turn
        for index, start in enumerate(range(0, len(text), _DELTA_CHARS)):
            if isinstance(turn, FailMidStream) and index == turn.after_deltas:
                raise RuntimeError("scripted mid-stream model failure")
            yield ResponseTextDeltaEvent(
                content_index=0,
                delta=text[start : start + _DELTA_CHARS],
                item_id="msg_mock",
                logprobs=[],
                output_index=0,
                sequence_number=next(seq),
                type="response.output_text.delta",
            )
        yield ResponseCompletedEvent(
            response=_response([_message(text)]),
            sequence_number=next(seq),
            type="response.completed",
        )

    @staticmethod
    def _tool_call(turn: ToolCall, index: int) -> ResponseFunctionToolCall:
        return ResponseFunctionToolCall(
            arguments=turn.arguments,
            call_id=f"call_mock_{index}",
            name=turn.name,
            type="function_call",
            id=f"fc_mock_{index}",
            status="completed",
        )


class ScriptedModelProvider(ModelProvider):
    """Hands out one shared model so the script advances across turns."""

    def __init__(self, script: list[ScriptEntry]) -> None:
        self._model = ScriptedStreamingModel(script)

    def get_model(self, model_name: str | None) -> Model:
        return self._model
