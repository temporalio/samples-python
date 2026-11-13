import uuid

from temporalio.client import Client
from temporalio.worker import Worker

from agent_framework_plugin.middleware.workflow import REMINDER, MiddlewareWorkflow
from tests.agent_framework_plugin._fake_chat_client import (
    function_call_response,
    scripted_plugin,
    text_response,
)
from tests.agent_framework_plugin.helpers import (
    INVOKE_MODEL,
    count_scheduled_activities,
    function_results,
    with_plugin,
)


async def test_middleware(client: Client) -> None:
    plugin, factory = scripted_plugin(
        [
            function_call_response(
                "delete_file", {"path": "/etc/passwd"}, call_id="c1"
            ),
            function_call_response(
                "delete_file", {"path": "/tmp/scratch.txt"}, call_id="c2"
            ),
            text_response("The first delete was refused; the second file is gone."),
        ]
    )
    client = with_plugin(client, plugin)
    task_queue = f"agent-framework-middleware-{uuid.uuid4()}"

    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[MiddlewareWorkflow],
        max_cached_workflows=0,
    ):
        handle = await client.start_workflow(
            MiddlewareWorkflow.run,
            "Delete /etc/passwd, then delete /tmp/scratch.txt.",
            id=f"agent-framework-middleware-{uuid.uuid4()}",
            task_queue=task_queue,
        )
        result = await handle.result()

    assert result == "The first delete was refused; the second file is gone."
    # Three model turns; both tool calls were handled in the Workflow.
    assert await count_scheduled_activities(handle) == {INVOKE_MODEL: 3}
    calls = factory().calls
    # The function middleware refused the first call without running the tool
    # and let the second one through.
    assert function_results(calls[-1]["messages"]) == [
        "Refused: /etc/passwd is outside /tmp/",
        "deleted /tmp/scratch.txt",
    ]
    # The chat middleware added the reminder to every model call.
    assert all(call["options"]["instructions"].endswith(REMINDER) for call in calls)
