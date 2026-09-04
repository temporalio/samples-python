import asyncio

from opentelemetry.exporter.prometheus import PrometheusMetricReader

from google_adk_agents.metrics.telemetry import install_meter_provider


async def main() -> None:
    install_meter_provider(PrometheusMetricReader())

    from google.adk.models import LLMRegistry
    from prometheus_client import start_http_server
    from temporalio.client import Client
    from temporalio.contrib.google_adk_agents import GoogleAdkPlugin
    from temporalio.worker import Worker

    from google_adk_agents.metrics.models.local_metrics_model import LocalMetricsModel
    from google_adk_agents.metrics.workflows.metrics_workflow import MetricsWorkflow

    LLMRegistry.register(LocalMetricsModel)
    start_http_server(port=9464, addr="127.0.0.1")
    plugin = GoogleAdkPlugin()
    client = await Client.connect("localhost:7233", plugins=[plugin])
    worker = Worker(
        client,
        task_queue="google-adk-agents-metrics",
        workflows=[MetricsWorkflow],
    )
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
