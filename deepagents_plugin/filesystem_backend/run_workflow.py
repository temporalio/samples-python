"""Start the filesystem backend workflow against a scratch directory.

The workflow's agent writes a file and reads it back; each file operation runs
as a ``deepagents.backend_op`` activity, so the real disk write happens in an
activity worker, not in workflow code.
"""

import asyncio
import os
import tempfile

from temporalio.client import Client

from deepagents_plugin.filesystem_backend.workflow import FilesystemAgent


async def main() -> None:
    client = await Client.connect(os.environ.get("TEMPORAL_ADDRESS", "localhost:7233"))

    # Choose the scratch directory here (client side), then pass it in — the
    # workflow itself never reads the environment or the filesystem.
    root_dir = os.environ.get("DEEPAGENTS_WORKDIR") or tempfile.mkdtemp(
        prefix="deepagents-fs-"
    )
    print(f"Agent working directory: {root_dir}")

    result = await client.execute_workflow(
        FilesystemAgent.run,
        args=[
            root_dir,
            "Write a short haiku about durability to notes.txt, then read it "
            "back and tell me what it says.",
        ],
        id="deepagents-filesystem-backend",
        task_queue="deepagents-filesystem-backend",
    )

    print(f"Result: {result}")
    print(f"Files written under: {root_dir}")


if __name__ == "__main__":
    asyncio.run(main())
