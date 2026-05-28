"""Start the structured output workflow."""

import asyncio
import os

from temporalio.client import Client
from temporalio.contrib.strands import StrandsPlugin

from strands_plugin.structured_output.workflow import StructuredOutputWorkflow


async def main() -> None:
    # Plugin on the client so the pydantic data converter is installed.
    client = await Client.connect(
        os.environ.get("TEMPORAL_ADDRESS", "localhost:7233"),
        plugins=[StrandsPlugin()],
    )

    person = await client.execute_workflow(
        StructuredOutputWorkflow.run,
        "John Smith is a 30 year-old software engineer.",
        id="strands-structured-output",
        task_queue="strands-structured-output",
    )

    print(f"name={person.name} age={person.age} occupation={person.occupation}")


if __name__ == "__main__":
    asyncio.run(main())
