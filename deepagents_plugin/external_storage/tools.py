"""Register the external-storage tool before the Worker starts."""

from datetime import timedelta

from langchain_core.tools import tool
from temporalio.common import RetryPolicy
from temporalio.deepagents import tool_as_activity

PAYLOAD_BYTES = 6 * 1024 * 1024


@tool
async def read_file(file_path: str) -> str:
    """Read a mock document containing exactly 6 MiB of text."""
    del file_path
    return "x" * PAYLOAD_BYTES


reader = tool_as_activity(
    read_file,
    start_to_close_timeout=timedelta(seconds=30),
    activity_options={"retry_policy": RetryPolicy(maximum_attempts=1)},
)
