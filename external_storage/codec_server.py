"""Run the codec server for the external_storage sample.

Sets up S3 access via aioboto3 against the mock service in ``s3.py``, then
serves the payload HTTP handler from :mod:`handler` configured with the same
codec and external storage that the worker and starter use.

``build_namespace_dispatcher`` routes by the ``X-Namespace`` request header
so a single codec server process can host different codec/storage
configurations per namespace — this sample only configures one ("default").

To use this server, set the Web UI's Remote Codec Endpoint (Settings → Data
Encoder) to the URL printed when the server starts.

Deliberately left out for sample simplicity: authentication (would slot in
as a middleware between CORS and the dispatcher), configurable listen
address/port, and structured logging/tracing.
"""

import asyncio
import logging
from typing import Awaitable, Callable, Iterable, Mapping

import aioboto3
from aiohttp import hdrs, web
from temporalio.contrib.aws.s3driver import S3StorageDriver
from temporalio.contrib.aws.s3driver.aioboto3 import new_aioboto3_client
from temporalio.converter import ExternalStorage

from external_storage.codec import CompressionCodec
from external_storage.handler import payload_routes
from external_storage.worker import (
    S3_ACCESS_KEY,
    S3_BUCKET,
    S3_ENDPOINT,
    S3_SECRET_KEY,
)

WEB_UI_ORIGIN = "http://localhost:8233"

logger = logging.getLogger(__name__)


@web.middleware
async def cors_middleware(
    request: web.Request,
    handler: Callable[[web.Request], Awaitable[web.StreamResponse]],
) -> web.StreamResponse:
    """Add CORS support so the Web UI can call the codec server from its origin."""
    allow_origin = request.headers.get(hdrs.ORIGIN) == WEB_UI_ORIGIN

    response: web.StreamResponse
    if request.method == "OPTIONS":
        response = web.Response()
        if allow_origin:
            response.headers[hdrs.ACCESS_CONTROL_ALLOW_METHODS] = "POST"
            response.headers[hdrs.ACCESS_CONTROL_ALLOW_HEADERS] = (
                "content-type,x-namespace"
            )
    else:
        # Catch HTTPException so CORS headers also land on error responses
        # (e.g. the dispatcher's 404 for an unknown namespace).
        try:
            response = await handler(request)
        except web.HTTPException as exc:
            response = exc

    if allow_origin:
        response.headers[hdrs.ACCESS_CONTROL_ALLOW_ORIGIN] = WEB_UI_ORIGIN

    if isinstance(response, web.HTTPException):
        raise response
    return response


def build_namespace_dispatcher(
    routes_by_namespace: Mapping[str, Iterable[web.RouteDef]],
) -> Callable[[web.Request], Awaitable[web.StreamResponse]]:
    """Build an aiohttp handler that dispatches by the X-Namespace header.

    Returns a single handler that the caller registers for every codec server
    URL (``/encode``, ``/decode``, ``/download``). The handler inspects the
    ``X-Namespace`` header on each request and forwards to the handler
    configured for that namespace + method + path combination.
    """
    # Pre-build the flat lookup table at construction so the per-request
    # dispatch is just two dictionary lookups.
    handler_map = {
        ns: {(r.method, r.path): r.handler for r in routes}
        for ns, routes in routes_by_namespace.items()
    }

    async def dispatch_by_namespace(request: web.Request) -> web.StreamResponse:
        # The Temporal Web UI passes the namespace it's viewing in the
        # X-Namespace header on every codec-server request. A single process
        # can therefore host different codec/storage configs per namespace
        # without needing per-namespace URL prefixes.
        namespace = request.headers.get("X-Namespace", "")
        handlers = handler_map.get(namespace)
        if handlers is None:
            logger.warning("dispatch: unknown namespace %r", namespace)
            raise web.HTTPNotFound()
        handler = handlers.get((request.method, request.path))
        if handler is None:
            logger.warning(
                "dispatch: no handler for %s %s in namespace %r",
                request.method,
                request.path,
                namespace,
            )
            raise web.HTTPNotFound()
        return await handler(request)

    return dispatch_by_namespace


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    session = aioboto3.Session()
    async with session.client(
        "s3",
        endpoint_url=S3_ENDPOINT,
        aws_access_key_id=S3_ACCESS_KEY,
        aws_secret_access_key=S3_SECRET_KEY,
        region_name="us-east-1",
    ) as s3_client:
        driver = S3StorageDriver(
            client=new_aioboto3_client(s3_client),
            bucket=S3_BUCKET,
        )

        # The dispatcher map drives per-namespace configuration. Add more
        # entries here to host additional namespaces with their own codec
        # chain and/or storage backend. Each value is a list of routes
        # produced by ``payload_routes``; the dispatcher reads the
        # X-Namespace header to pick the right one per request.
        dispatch_by_namespace = build_namespace_dispatcher(
            {
                "default": payload_routes(
                    external_storage=ExternalStorage(drivers=[driver]),
                    prestorage_codec=CompressionCodec(),
                ),
            }
        )

        app = web.Application(middlewares=[cors_middleware])
        app.add_routes(
            [
                web.post("/encode", dispatch_by_namespace),
                web.post("/decode", dispatch_by_namespace),
                web.post("/download", dispatch_by_namespace),
            ]
        )

        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "127.0.0.1", 8081)
        await site.start()
        print("Codec server running at http://127.0.0.1:8081, ctrl+c to exit")
        try:
            await asyncio.Event().wait()
        except (KeyboardInterrupt, asyncio.CancelledError):
            pass
        finally:
            await runner.cleanup()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
