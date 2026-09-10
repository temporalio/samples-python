import uuid

import pytest
from google.adk.models import BaseLlm, LLMRegistry
from opentelemetry.sdk.metrics.export import HistogramDataPoint, InMemoryMetricReader
from temporalio.client import Client
from temporalio.contrib.google_adk_agents import GoogleAdkPlugin
from temporalio.worker import Replayer, Worker

from google_adk_agents.metrics.models.local_metrics_model import (
    MODEL_NAME,
    LocalMetricsModel,
)
from google_adk_agents.metrics.telemetry import install_meter_provider
from google_adk_agents.metrics.workflows.metrics_workflow import MetricsWorkflow

ADK_METER_SCOPE = "gcp.vertex.agent"


async def test_metrics_are_not_inflated_by_replay(
    client: Client, monkeypatch: pytest.MonkeyPatch
) -> None:
    reader = InMemoryMetricReader()
    install_meter_provider(reader)

    original_new_llm = LLMRegistry.new_llm

    def new_llm(model: str) -> BaseLlm:
        if model == MODEL_NAME:
            return LocalMetricsModel(model=model)
        return original_new_llm(model)

    monkeypatch.setattr(LLMRegistry, "new_llm", staticmethod(new_llm))

    plugin = GoogleAdkPlugin()
    config = client.config()
    config["plugins"] = [*config["plugins"], plugin]
    client = Client(**config)
    task_queue = f"google-adk-agents-metrics-{uuid.uuid4()}"
    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[MetricsWorkflow],
    ):
        handle = await client.start_workflow(
            MetricsWorkflow.run,
            "Explain replay-safe metrics.",
            id=f"google-adk-agents-metrics-{uuid.uuid4()}",
            task_queue=task_queue,
        )
        result = await handle.result()
        history = await handle.fetch_history()

    assert result == "Replay-safe metrics are ready."
    counts_before_replay = metric_counts(reader)
    assert counts_before_replay["gen_ai.invoke_agent.duration"] > 0
    assert counts_before_replay["gen_ai.invoke_agent.inference_calls"] > 0
    assert counts_before_replay["gen_ai.client.operation.duration"] > 0
    assert counts_before_replay["gen_ai.client.token.usage"] > 0

    await Replayer(workflows=[MetricsWorkflow], plugins=[plugin]).replay_workflow(
        history
    )

    assert metric_counts(reader) == counts_before_replay


def metric_counts(reader: InMemoryMetricReader) -> dict[str, int]:
    counts: dict[str, int] = {}
    data = reader.get_metrics_data()
    if data is not None:
        for resource_metrics in data.resource_metrics:
            for scope_metrics in resource_metrics.scope_metrics:
                if scope_metrics.scope.name != ADK_METER_SCOPE:
                    continue
                for metric in scope_metrics.metrics:
                    count = 0
                    for point in metric.data.data_points:
                        if not isinstance(point, HistogramDataPoint):
                            raise TypeError(f"Unexpected metric point: {type(point)}")
                        count += point.count
                    counts[metric.name] = count
    return counts
