import dataclasses
from typing import Any, Optional, Type

import temporalio.converter
from temporalio.api.common.v1 import Payload
from temporalio.converter import (
    CompositePayloadConverter,
    DefaultPayloadConverter,
    EncodingPayloadConverter,
)


class GreetingInput:
    def __init__(self, name: str) -> None:
        self.name = name


class GreetingOutput:
    def __init__(self, result: str) -> None:
        self.result = result


class GreetingEncodingPayloadConverter(EncodingPayloadConverter):
    @property
    def encoding(self) -> str:
        return "text/my-greeting-encoding"

    def to_payload(self, value: Any) -> Optional[Payload]:
        if isinstance(value, GreetingInput):
            return Payload(
                metadata={"encoding": self.encoding.encode(), "is_input": b"true"},
                data=value.name.encode(),
            )
        elif isinstance(value, GreetingOutput):
            return Payload(
                metadata={"encoding": self.encoding.encode()},
                data=value.result.encode(),
            )
        else:
            return None

    def from_payload(self, payload: Payload, type_hint: Optional[Type] = None) -> Any:
        if payload.metadata.get("is_input") == b"true":
            # Confirm proper type hint if present
            assert not type_hint or type_hint is GreetingInput
            return GreetingInput(payload.data.decode())
        else:
            assert not type_hint or type_hint is GreetingOutput
            return GreetingOutput(payload.data.decode())


class GreetingPayloadConverter(CompositePayloadConverter):
    def __init__(self) -> None:
        # Just add ours as first before the defaults
        super().__init__(
            GreetingEncodingPayloadConverter(),
            *DefaultPayloadConverter.default_encoding_payload_converters
        )


# Use the default data converter, but change the payload converter.
greeting_data_converter = dataclasses.replace(
    temporalio.converter.default(),
    payload_converter_class=GreetingPayloadConverter,
)
