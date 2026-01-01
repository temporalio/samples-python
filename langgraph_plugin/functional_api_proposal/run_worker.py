"""Worker for the LangGraph Functional API sample.

This shows the proposed developer experience with LangGraphFunctionalPlugin.

Key insight: LangGraph doesn't pre-register tasks. When @task functions are
called, they go through CONFIG_KEY_CALL which receives the actual function
object. The `identifier()` function returns `module.qualname` for the function.

This means we DON'T need explicit task registration! The plugin can:
1. Inject CONFIG_KEY_CALL callback that schedules a dynamic activity
2. The activity receives the function identifier (module.qualname) + args
3. The activity imports and executes the function

The worker just needs the task modules to be importable.
"""

import asyncio
from datetime import timedelta

from temporalio.client import Client
from temporalio.contrib.langgraph import LangGraphFunctionalPlugin  # type: ignore[attr-defined]
from temporalio.envconfig import ClientConfig
from temporalio.worker import Worker

from langgraph_plugin.functional_api_proposal.entrypoint import (
    document_workflow,
    review_workflow,
)
from langgraph_plugin.functional_api_proposal.workflow import (
    DocumentWorkflow,
    ReviewWorkflow,
)

# Note: tasks module is NOT imported here - tasks are discovered dynamically
# at runtime when called within the entrypoint. The worker just needs the
# module to be importable (which it is since it's in the Python path).


async def main() -> None:
    # Create the functional plugin
    #
    # NO explicit task registration needed!
    # Tasks are discovered dynamically when called via CONFIG_KEY_CALL.
    # The callback receives the function object and uses identifier() to get
    # the module.qualname (e.g., "langgraph_plugin.functional_api_proposal.tasks.research_topic")
    #
    # Entrypoints are passed as a list - plugin extracts names from func.__name__
    plugin = LangGraphFunctionalPlugin(
        # Pass entrypoint functions directly - names extracted from __name__
        entrypoints=[document_workflow, review_workflow],
        # Default timeout for dynamically discovered task activities
        default_task_timeout=timedelta(minutes=10),
        # Per-task options by function name (optional)
        task_options={
            "research_topic": {
                "start_to_close_timeout": timedelta(minutes=15),
                "retry_policy": {"maximum_attempts": 5},
            },
        },
    )

    # Connect to Temporal with the plugin
    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")
    client = await Client.connect(**config, plugins=[plugin])

    # Create worker with user-defined workflows
    # Note: The plugin provides a single dynamic activity that can execute any task
    worker = Worker(
        client,
        task_queue="langgraph-functional",
        workflows=[DocumentWorkflow, ReviewWorkflow],
    )

    print("Worker started on task queue 'langgraph-functional'")
    print("Press Ctrl+C to exit.")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
