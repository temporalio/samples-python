"""Client that starts a Nexus operation with a completion callback."""

import asyncio
import uuid
from datetime import timedelta

from temporalio import nexus
from temporalio.client import Client
from temporalio.envconfig import ClientConfig

from nexus_completion_callbacks.caller.completion_handler import (
    CallbackContext,
    GreetingCompletionHandler,
)
from nexus_completion_callbacks.caller.completion_worker import COMPLETION_TASK_QUEUE
from nexus_completion_callbacks.service import (
    GreetingInput,
    GreetingService,
)

ENDPOINT_NAME = "nexus-completion-callbacks-endpoint"


async def main() -> None:
    config = ClientConfig.load_client_connect_config()
    _ = config.setdefault("target_host", "localhost:7233")
    client = await Client.connect(**config)

    operation_id = f"greeting-{uuid.uuid4()}"
    nexus_client = client.create_nexus_client(
        service=GreetingService,
        endpoint=ENDPOINT_NAME,
    )
    _ = await nexus_client.start_operation(
        GreetingService.greet,
        GreetingInput(name="World"),
        id=operation_id,
        schedule_to_close_timeout=timedelta(seconds=10),
        completion_callbacks=[
            nexus.create_completion_callback(
                operation=GreetingCompletionHandler.on_complete,
                task_queue=COMPLETION_TASK_QUEUE,
                source_context=CallbackContext(operation_id=operation_id),
            )
        ],
    )
    # The starter does not wait for the result. The server delivers it to the
    # completion Worker when the operation finishes.
    print(f"Started operation {operation_id}")


if __name__ == "__main__":
    asyncio.run(main())
