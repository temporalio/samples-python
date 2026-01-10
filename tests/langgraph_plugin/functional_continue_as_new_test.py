"""Tests for the Continue-as-New Functional API sample."""

import uuid
from datetime import timedelta

import pytest
from temporalio.client import Client
from temporalio.contrib.langgraph import LangGraphPlugin, activity_options
from temporalio.worker import Worker

from langgraph_plugin.functional_api.continue_as_new.entrypoint import (
    pipeline_entrypoint,
)
from langgraph_plugin.functional_api.continue_as_new.workflow import (
    ContinueAsNewWorkflow,
    PipelineInput,
)


@pytest.mark.asyncio
async def test_continue_as_new_workflow(client: Client) -> None:
    """Test that the continue-as-new workflow executes correctly.

    Verifies:
    1. Phase 1 executes tasks 1-3
    2. Continue-as-new passes checkpoint
    3. Phase 2 completes with all 5 tasks
    4. Final result is correct (165)
    """
    plugin = LangGraphPlugin(
        graphs={"pipeline_entrypoint": pipeline_entrypoint},
        default_activity_options=activity_options(
            start_to_close_timeout=timedelta(seconds=30),
        ),
    )

    new_config = client.config()
    existing_plugins = new_config.get("plugins", [])
    new_config["plugins"] = list(existing_plugins) + [plugin]
    plugin_client = Client(**new_config)

    task_queue = f"test-continue-as-new-{uuid.uuid4()}"

    async with Worker(
        plugin_client,
        task_queue=task_queue,
        workflows=[ContinueAsNewWorkflow],
    ):
        result = await plugin_client.execute_workflow(
            ContinueAsNewWorkflow.run,
            PipelineInput(value=10),
            id=f"test-continue-as-new-{uuid.uuid4()}",
            task_queue=task_queue,
            execution_timeout=timedelta(seconds=60),
        )

        # Verify correct final result
        # 10 * 2 = 20 -> 20 + 5 = 25 -> 25 * 3 = 75 -> 75 - 10 = 65 -> 65 + 100 = 165
        assert result["result"] == 165
        assert result["completed_tasks"] == 5
