import asyncio
import os

from temporalio.claude_agent_sdk import ClaudeAgentSDKPlugin
from temporalio.client import Client
from temporalio.contrib.opentelemetry import OpenTelemetryPlugin
from temporalio.worker import Worker

from claude_agent_sdk_plugin.offline import Answer, offline_api_without_key, tool_use
from claude_agent_sdk_plugin.open_telemetry.telemetry import (
    CLAUDE_CODE_TRACING,
    install_tracer_provider,
)
from claude_agent_sdk_plugin.open_telemetry.workflow import OpenTelemetryWorkflow

OFFLINE_ANSWERS: dict[str, Answer] = {
    "How many Python files": tool_use(
        "toolu_count",
        "Bash",
        command="ls *.py | wc -l",
        description="Count the Python files",
    ),
    "tool_result:toolu_count": "I counted the Python files with ls.",
}


async def main() -> None:
    install_tracer_provider("claude-agent-sdk-worker")
    client = await Client.connect(
        os.environ.get("TEMPORAL_ADDRESS", "localhost:7233"),
        plugins=[OpenTelemetryPlugin(add_temporal_spans=True)],
    )

    with offline_api_without_key(OFFLINE_ANSWERS):
        os.environ.update(CLAUDE_CODE_TRACING)
        worker = Worker(
            client,
            task_queue="claude-agent-sdk-open-telemetry",
            workflows=[OpenTelemetryWorkflow],
            plugins=[ClaudeAgentSDKPlugin()],
        )
        await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
