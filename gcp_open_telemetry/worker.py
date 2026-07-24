"""Run an OpenTelemetry-instrumented Temporal Worker on Cloud Run."""

from __future__ import annotations

import asyncio
import os
import signal
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import timedelta

from temporalio.client import Client
from temporalio.contrib.gcp import DEFAULT_METRIC_PERIODICITY, OpenTelemetryPlugin
from temporalio.worker import Worker

from gcp_open_telemetry.workflow import GreetingWorkflow, compose_greeting

COLLECTOR_HOST = "127.0.0.1"
COLLECTOR_PORT = 4317
COLLECTOR_STARTUP_TIMEOUT = timedelta(seconds=60)
WORKER_GRACEFUL_SHUTDOWN_TIMEOUT = timedelta(seconds=5)
TRACE_FLUSH_TIMEOUT = timedelta(seconds=2)


@dataclass(frozen=True)
class WorkerSettings:
    """Environment-backed Temporal connection settings."""

    address: str
    namespace: str
    task_queue: str
    api_key: str

    @classmethod
    def from_environment(
        cls, environment: Mapping[str, str] | None = None
    ) -> WorkerSettings:
        env = os.environ if environment is None else environment
        namespace = _required(env, "TEMPORAL_NAMESPACE")
        return cls(
            address=_optional(env, "TEMPORAL_ADDRESS")
            or f"{namespace}.tmprl.cloud:7233",
            namespace=namespace,
            task_queue=_required(env, "TEMPORAL_TASK_QUEUE"),
            # Secret Manager preserves trailing newlines from the source file.
            api_key=_required(env, "TEMPORAL_API_KEY"),
        )


def _required(environment: Mapping[str, str], name: str) -> str:
    value = _optional(environment, name)
    if value is None:
        raise RuntimeError(f"{name} must be set to a non-empty value")
    return value


def _optional(environment: Mapping[str, str], name: str) -> str | None:
    value = environment.get(name)
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


async def wait_for_collector(
    *,
    host: str = COLLECTOR_HOST,
    port: int = COLLECTOR_PORT,
    timeout: timedelta = COLLECTOR_STARTUP_TIMEOUT,
) -> None:
    """Wait until the local OTLP gRPC socket accepts connections."""
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout.total_seconds()
    last_error: OSError | None = None

    while loop.time() < deadline:
        try:
            _, writer = await asyncio.open_connection(host, port)
            writer.close()
            await writer.wait_closed()
            return
        except OSError as err:
            last_error = err
            await asyncio.sleep(0.5)

    raise RuntimeError(
        f"OpenTelemetry Collector did not listen on {host}:{port} "
        f"within {timeout.total_seconds():g} seconds"
    ) from last_error


async def run_worker() -> None:
    """Connect to Temporal and run until Cloud Run requests shutdown."""
    settings = WorkerSettings.from_environment()
    await wait_for_collector()

    expected_metric_periodicity = timedelta(seconds=60)
    if DEFAULT_METRIC_PERIODICITY != expected_metric_periodicity:
        raise RuntimeError(
            "Expected the coordinated 60-second GCP metric periodicity, got "
            f"{DEFAULT_METRIC_PERIODICITY}"
        )

    # @@@SNIPSTART python-cloud-run-otel-worker
    # Endpoint, service name, Core metrics, and tracer provider all use the GCP
    # plugin defaults. The opt-in adds named Temporal operation spans.
    plugin = OpenTelemetryPlugin(add_temporal_spans=True)
    client = await Client.connect(
        settings.address,
        namespace=settings.namespace,
        api_key=settings.api_key,
        tls=True,
        plugins=[plugin],
    )
    worker = Worker(
        client,
        task_queue=settings.task_queue,
        workflows=[GreetingWorkflow],
        activities=[compose_greeting],
        graceful_shutdown_timeout=WORKER_GRACEFUL_SHUTDOWN_TIMEOUT,
    )
    # @@@SNIPEND

    loop = asyncio.get_running_loop()
    shutdown_requested = False

    def request_shutdown() -> None:
        nonlocal shutdown_requested
        if shutdown_requested:
            return
        shutdown_requested = True
        print("Worker shutdown requested", flush=True)
        loop.create_task(worker.shutdown())

    for signum in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(signum, request_shutdown)

    print(
        "Worker starting "
        f"task_queue={settings.task_queue} "
        f"otel_endpoint={plugin.endpoint} "
        f"service_name={plugin.service_name} "
        f"metric_periodicity={DEFAULT_METRIC_PERIODICITY.total_seconds():g}s",
        flush=True,
    )
    try:
        await worker.run()
    finally:
        traces_flushed = await asyncio.to_thread(plugin.shutdown, TRACE_FLUSH_TIMEOUT)
        print(f"Worker stopped traces_flushed={traces_flushed}", flush=True)


if __name__ == "__main__":
    asyncio.run(run_worker())
