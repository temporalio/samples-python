"""Run an OpenTelemetry-instrumented Temporal Worker on a Cloud Run worker pool."""

from __future__ import annotations

import asyncio
import signal
from datetime import timedelta

from temporalio.client import Client
from temporalio.contrib.gcp.cloud_run.opentelemetry import OpenTelemetryPlugin
from temporalio.worker import Worker

from gcp.cloud_run.opentelemetry.settings import load_settings
from gcp.cloud_run.opentelemetry.workflow import GreetingWorkflow, compose_greeting

COLLECTOR_HOST = "127.0.0.1"
COLLECTOR_PORT = 4317
COLLECTOR_STARTUP_TIMEOUT = timedelta(seconds=60)
WORKER_GRACEFUL_SHUTDOWN_TIMEOUT = timedelta(seconds=5)
TRACE_FLUSH_TIMEOUT = timedelta(seconds=2)


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


async def main() -> None:
    settings = load_settings()
    await wait_for_collector()

    # @@@SNIPSTART python-cloud-run-otel-worker
    plugin = OpenTelemetryPlugin(add_temporal_spans=True)
    client = await Client.connect(
        settings.address,
        namespace=settings.namespace,
        api_key=settings.api_key,
        tls=settings.tls,
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
        f"service_name={plugin.service_name}",
        flush=True,
    )
    try:
        await worker.run()
    finally:
        traces_flushed = await asyncio.to_thread(plugin.shutdown, TRACE_FLUSH_TIMEOUT)
        print(f"Worker stopped traces_flushed={traces_flushed}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
