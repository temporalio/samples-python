import uuid

from opentelemetry.sdk.metrics.export import InMemoryMetricReader

from google_adk_agents.metrics.telemetry import install_meter_provider

ADK_METER_SCOPE = "gcp.vertex.agent"


async def test_metrics_are_not_inflated_by_replay() -> None:
    reader = InMemoryMetricReader()
    install_meter_provider(reader)

    from google.adk.models import LLMRegistry
    from temporalio.contrib.google_adk_agents import GoogleAdkPlugin
    from temporalio.testing import WorkflowEnvironment
    from temporalio.worker import Worker

    from google_adk_agents.metrics.models.local_metrics_model import LocalMetricsModel
    from google_adk_agents.metrics.workflows.metrics_workflow import MetricsWorkflow

    LLMRegistry.register(LocalMetricsModel)
    async with await WorkflowEnvironment.start_time_skipping() as environment:
        plugin = GoogleAdkPlugin()
        config = environment.client.config()
        config["plugins"] = [*config["plugins"], plugin]
        client = type(environment.client)(**config)
        task_queue = f"google-adk-agents-metrics-{uuid.uuid4()}"
        async with Worker(
            client,
            task_queue=task_queue,
            workflows=[MetricsWorkflow],
            plugins=[plugin],
            max_cached_workflows=0,
        ):
            result = await client.execute_workflow(
                MetricsWorkflow.run,
                "Explain replay-safe metrics.",
                id=f"google-adk-agents-metrics-{uuid.uuid4()}",
                task_queue=task_queue,
            )

    assert result == "Replay-safe metrics are ready."
    counts: dict[str, int] = {}
    data = reader.get_metrics_data()
    if data is not None:
        for resource_metrics in data.resource_metrics:
            for scope_metrics in resource_metrics.scope_metrics:
                if scope_metrics.scope.name != ADK_METER_SCOPE:
                    continue
                for metric in scope_metrics.metrics:
                    counts[metric.name] = sum(
                        getattr(point, "count", 1) for point in metric.data.data_points
                    )
    assert counts["gen_ai.invoke_agent.duration"] == 1
    assert counts["gen_ai.invoke_agent.inference_calls"] == 1
    assert counts["gen_ai.client.operation.duration"] == 1
    assert counts["gen_ai.client.token.usage"] == 2
