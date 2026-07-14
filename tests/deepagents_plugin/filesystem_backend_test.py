import uuid

from langchain_core.messages import AIMessage
from temporalio.client import Client
from temporalio.contrib.deepagents import DeepAgentsPlugin
from temporalio.contrib.deepagents.testing import mock_model_provider
from temporalio.worker import Worker

from deepagents_plugin.filesystem_backend.workflow import FilesystemAgent


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
        result = await client.execute_workflow(
            FilesystemAgent.run,
            args=[str(tmp_path), "Write 'hello' to notes.txt and read it back."],
            id=f"deepagents-filesystem-backend-{uuid.uuid4()}",
            task_queue=task_queue,
        )

    assert "hello" in result
    # The write really landed on disk — performed in the backend_op activity.
    assert (tmp_path / "notes.txt").read_text() == "hello"
