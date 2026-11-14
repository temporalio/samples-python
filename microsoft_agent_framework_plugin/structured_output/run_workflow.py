"""Start the structured output workflow and print the typed result."""

# @@@SNIPSTART python-microsoft-agent-framework-structured-output-run-workflow
import asyncio
import os

from temporalio.client import Client
from temporalio.microsoft_agent_framework import MicrosoftAgentFrameworkPlugin

from microsoft_agent_framework_plugin.structured_output.workflow import (
    StructuredOutputWorkflow,
)


async def main() -> None:
    # The plugin on this client installs the Pydantic data converter, which
    # decodes the Workflow's PersonInfo result.
    client = await Client.connect(
        os.environ.get("TEMPORAL_ADDRESS", "localhost:7233"),
        plugins=[MicrosoftAgentFrameworkPlugin()],
    )

    person = await client.execute_workflow(
        StructuredOutputWorkflow.run,
        "John Smith is a 30 year-old software engineer.",
        id="microsoft-agent-framework-structured-output",
        task_queue="microsoft-agent-framework-structured-output",
    )

    print(f"name={person.name} age={person.age} occupation={person.occupation}")


if __name__ == "__main__":
    asyncio.run(main())
# @@@SNIPEND
