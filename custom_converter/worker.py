import asyncio
import dataclasses
from typing import Any, Optional, Type

import temporalio.converter
from temporalio import workflow
from temporalio.api.common.v1 import Payload
from temporalio.client import Client
from temporalio.converter import (
    CompositePayloadConverter,
    DefaultPayloadConverter,
    EncodingPayloadConverter,
)
from temporalio.worker import Worker


class GreetingInput:
    def __init__(self, name: str) -> None:
        self.name = name


class GreetingOutput:
    def __init__(self, result: str) -> None:
        self.result = result


@workflow.defn
class GreetingWorkflow:
    @workflow.run
    async def run(self, input: GreetingInput) -> GreetingOutput:
        return GreetingOutput(f"Hello, {input.name}")


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
            # TODO(cretz): Make this list available without instantiation - https://github.com/temporalio/sdk-python/issues/139
            *DefaultPayloadConverter().converters.values(),
        )


interrupt_event = asyncio.Event()


async def main():
    # Connect client
    client = await Client.connect(
        "localhost:7233",
        # Use the default data converter, but change the payload converter.
        # Without this, when trying to run a workflow, we get:
        #   KeyError: 'Unknown payload encoding my-greeting-encoding
        data_converter=dataclasses.replace(
            temporalio.converter.default(),
            payload_converter_class=GreetingPayloadConverter,
        ),
    )

    # Run a worker for the workflow
    async with Worker(
        client,
        task_queue="custom_converter-task-queue",
        workflows=[GreetingWorkflow],
    ):
        # Wait until interrupted
        print("Worker started, ctrl+c to exit")
        await interrupt_event.wait()
        print("Shutting down")


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        interrupt_event.set()
        loop.run_until_complete(loop.shutdown_asyncgens())
