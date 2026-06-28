"""Start the files workflow.

The file is read on the worker, so ``sample.txt`` must be on a path the worker
process can access (here it ships alongside this sample).
"""

# @@@SNIPSTART python-google-genai-files-run-workflow
import asyncio
import os
from pathlib import Path

from temporalio.client import Client

from google_genai_plugin.files.workflow import FilesWorkflow

SAMPLE_FILE = str(Path(__file__).parent / "sample.txt")


async def main() -> None:
    client = await Client.connect(os.environ.get("TEMPORAL_ADDRESS", "localhost:7233"))

    result = await client.execute_workflow(
        FilesWorkflow.run,
        args=[SAMPLE_FILE, "Summarize this document in one sentence."],
        id="google-genai-files",
        task_queue="google-genai-files",
    )

    print(f"Result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
# @@@SNIPEND
