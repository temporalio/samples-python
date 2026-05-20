"""Scripted Strands model for sample tests.

Vendored from the SDK's ``tests/contrib/strands/mock_model.py``. Each entry in
``responses`` drives one ``stream()`` call: a ``str`` yields a text turn, a
``dict`` of ``{"name", "input"}`` yields a tool-use turn.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterable
from typing import Any

from strands.models import Model
from strands.types.streaming import StreamEvent

import temporalio.contrib.strands._plugin as _plugin_module


class MockModel(Model):
    def __init__(self, responses: list[str | dict[str, Any]]) -> None:
        self._responses = list(responses)
        self._tool_call_index = 0

    def update_config(self, **_model_config: Any) -> None:
        return None

    def get_config(self) -> dict[str, Any]:
        return {}

    def structured_output(self, *_args: Any, **_kwargs: Any):
        raise NotImplementedError

    async def stream(self, *_args: Any, **_kwargs: Any) -> AsyncIterable[StreamEvent]:
        if not self._responses:
            raise AssertionError("MockModel script exhausted")
        response = self._responses.pop(0)

        yield {"messageStart": {"role": "assistant"}}

        if isinstance(response, str):
            yield {"contentBlockDelta": {"delta": {"text": response}}}
            yield {"contentBlockStop": {}}
            yield {"messageStop": {"stopReason": "end_turn"}}
        else:
            self._tool_call_index += 1
            yield {
                "contentBlockStart": {
                    "start": {
                        "toolUse": {
                            "name": response["name"],
                            "toolUseId": f"mock-tool-{self._tool_call_index}",
                        },
                    },
                },
            }
            yield {
                "contentBlockDelta": {
                    "delta": {"toolUse": {"input": json.dumps(response["input"])}},
                },
            }
            yield {"contentBlockStop": {}}
            yield {"messageStop": {"stopReason": "tool_use"}}


def patch_bedrock(monkeypatch: Any, responses: list[Any]) -> None:
    """Make the plugin's implicit BedrockModel factory return a scripted MockModel."""
    monkeypatch.setattr(
        _plugin_module, "BedrockModel", lambda *a, **kw: MockModel(responses)
    )
