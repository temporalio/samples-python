"""Client that executes the activity-backed Nexus operation."""

import asyncio
import uuid
from datetime import timedelta

from temporalio.client import Client
from temporalio.envconfig import ClientConfig

from nexus_standalone_activity.service import GreetingInput, GreetingService

ENDPOINT_NAME = "nexus-standalone-activity-endpoint"


async def main() -> None:
    config = ClientConfig.load_client_connect_config()
    _ = config.setdefault("target_host", "localhost:7233")
    client = await Client.connect(**config)

    nexus_client = client.create_nexus_client(
        service=GreetingService,
        endpoint=ENDPOINT_NAME,
    )
    result = await nexus_client.execute_operation(
        GreetingService.greet,
        GreetingInput(name="World"),
        id=f"greeting-{uuid.uuid4()}",
        schedule_to_close_timeout=timedelta(seconds=10),
    )
    print(result.message)


if __name__ == "__main__":
    asyncio.run(main())
