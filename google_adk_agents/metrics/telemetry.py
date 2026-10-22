import opentelemetry.metrics
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import MetricReader
from temporalio.contrib.opentelemetry import ReplaySafeMeterProvider


def install_meter_provider(reader: MetricReader) -> ReplaySafeMeterProvider:
    provider = ReplaySafeMeterProvider(MeterProvider(metric_readers=[reader]))
    opentelemetry.metrics.set_meter_provider(provider)
    if opentelemetry.metrics.get_meter_provider() is not provider:
        raise RuntimeError("The global OpenTelemetry meter provider is already set")
    return provider
