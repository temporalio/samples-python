import uuid

from langchain_core.messages import AIMessage
from temporalio.client import Client
from temporalio.contrib.deepagents import DeepAgentsPlugin
from temporalio.contrib.deepagents.testing import mock_model_provider
from temporalio.worker import Worker

from deepagents_plugin.filesystem_backend.workflow import FilesystemAgent
from tests.deepagents_plugin.helpers import BACKEND_OP, count_scheduled_activities


async def test_filesystem_backend(client: Client, tmp_path) -> None:
    # Script the agent's built-in file tools: write the note, read it back, then
    # report. Each file op crosses the activity boundary via TemporalBackend, so
    # the real disk write happens in an activity, not in workflow code.
    write_turn = AIMessage(
        content="",
        tool_calls=[
            {
                "name": "write_file",
                "args": {"file_path": "/notes.txt", "content": "hello"},
                "id": "call-write",
            }
        ],
    )
    read_turn = AIMessage(
        content="",
        tool_calls=[
            {
                "name": "read_file",
                "args": {"file_path": "/notes.txt"},
                "id": "call-read",
            }
        ],
    )
    final = AIMessage(content="The note says: hello")
    plugin = DeepAgentsPlugin(
        model_provider=mock_model_provider([write_turn, read_turn, final]),
    )
    task_queue = f"deepagents-filesystem-backend-{uuid.uuid4()}"

    config = client.config()
    config["plugins"] = [*config["plugins"], plugin]
    client = Client(**config)

    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[FilesystemAgent],
        max_cached_workflows=0,
    ):
        handle = await client.start_workflow(
            FilesystemAgent.run,
            args=[str(tmp_path), "Write 'hello' to notes.txt and read it back."],
            id=f"deepagents-filesystem-backend-{uuid.uuid4()}",
            task_queue=task_queue,
        )
        result = await handle.result()

    assert "hello" in result
    # The write really landed on disk...
    assert (tmp_path / "notes.txt").read_text() == "hello"
    # ...and the file ops really crossed the activity boundary (write + read as
    # backend_op activities) — the on-disk assert alone cannot distinguish an
    # in-workflow write in this single-process test.
    counts = await count_scheduled_activities(handle)
    assert counts[BACKEND_OP] >= 2, counts
