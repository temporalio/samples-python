"""
Temporal Worker for Google Cloud Run.

Reads connection config from environment variables, registers a sample Workflow
and Activity, and handles SIGTERM gracefully so Cloud Run can shut the container
down within its 10-second termination window.

Run from the repo root:

    TEMPORAL_ADDRESS=localhost:7233 TEMPORAL_NAMESPACE=default \\
        uv run python -m cloud_run_worker.worker
"""

import asyncio
import logging
import os
import signal
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from temporalio.client import Client, TLSConfig
from temporalio.worker import Worker

from cloud_run_worker.activities import hello_activity
from cloud_run_worker.workflows import TASK_QUEUE, SampleWorkflow

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class _HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, *_args) -> None:  # silence per-request access logs
        pass


def _start_health_server() -> None:
    """Serve HTTP 200 on $PORT so Cloud Run's startup probe passes.

    Cloud Run's container contract requires the container to listen on the
    port named by $PORT. A Temporal worker only polls Temporal, so we run a
    tiny health endpoint in a daemon thread to satisfy that contract.
    """
    port = int(os.environ.get("PORT", "8080"))
    server = HTTPServer(("0.0.0.0", port), _HealthHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    logger.info("Health server listening on :%d", port)


def _tls_config() -> TLSConfig | None:
    """Return a TLSConfig when mTLS env vars are present, otherwise None."""
    cert_b64 = os.environ.get("TEMPORAL_TLS_CERT")
    key_b64 = os.environ.get("TEMPORAL_TLS_KEY")
    if cert_b64 and key_b64:
        import base64

        return TLSConfig(
            client_cert=base64.b64decode(cert_b64),
            client_private_key=base64.b64decode(key_b64),
        )
    return None


async def run() -> None:
    # Open the health port first so Cloud Run's startup probe passes even
    # while the Temporal connection is still being established.
    _start_health_server()

    address = os.environ.get("TEMPORAL_ADDRESS", "localhost:7233")
    namespace = os.environ.get("TEMPORAL_NAMESPACE", "default")
    task_queue = os.environ.get("TEMPORAL_TASK_QUEUE", TASK_QUEUE)

    logger.info(
        "Connecting to Temporal at %s (namespace=%s, task_queue=%s)",
        address,
        namespace,
        task_queue,
    )

    client = await Client.connect(
        address,
        namespace=namespace,
        tls=_tls_config() or False,
    )

    shutdown_event = asyncio.Event()

    def _handle_sigterm(*_) -> None:  # noqa: ANN002
        logger.info("SIGTERM received — initiating graceful shutdown")
        shutdown_event.set()

    signal.signal(signal.SIGTERM, _handle_sigterm)
    signal.signal(signal.SIGINT, _handle_sigterm)

    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[SampleWorkflow],
        activities=[hello_activity],
    ):
        logger.info(
            "Worker running on task queue %r. Waiting for shutdown signal.", task_queue
        )
        await shutdown_event.wait()

    logger.info("Worker shut down cleanly.")


if __name__ == "__main__":
    asyncio.run(run())
