import uuid

from logfire.testing import CaptureLogfire
from temporalio.client import Client
from temporalio.contrib.opentelemetry import TracingInterceptor
from temporalio.worker import Worker

from pydantic_ai.durable_exec.temporal import LogfirePlugin, PydanticAIPlugin
from pydantic_ai_plugin.logfire.workflow import (
    ObservabilityInput,
    ObservabilityWorkflow,
)


async def test_logfire_plugin_traces_durable_agent(
    client: Client, capfire: CaptureLogfire
) -> None:
    traced = await Client.connect(
        client.service_client.config.target_host,
        plugins=[PydanticAIPlugin(), LogfirePlugin(metrics=False)],
    )
    assert any(
        isinstance(interceptor, TracingInterceptor)
        for interceptor in traced.config(active_config=True)["interceptors"]
    )

    task_queue = f"pydantic-ai-logfire-{uuid.uuid4()}"
    async with Worker(
        traced,
        task_queue=task_queue,
        workflows=[ObservabilityWorkflow],
        max_cached_workflows=0,
    ):
        result = await traced.execute_workflow(
            ObservabilityWorkflow.run,
            ObservabilityInput(prompt="Trace this run."),
            id=f"pydantic-ai-logfire-{uuid.uuid4()}",
            task_queue=task_queue,
        )

    assert result == "This run is traced."
    span_names = [span["name"] for span in capfire.exporter.exported_spans_as_dict()]
    assert any("observable_agent" in name for name in span_names), span_names
    assert any("Workflow" in name for name in span_names), span_names
