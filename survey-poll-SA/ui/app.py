"""FastAPI dashboard backend for the survey-poll sample.

A single background asyncio task polls the PollAggregatorWorkflow every
`POLL_INTERVAL_SECONDS` and caches the latest TallyResult in this process.
`GET /tally` serves the cache immediately without issuing a Temporal Query,
so any number of browser tabs or rapid reloads cost nothing extra.

This is the fix for the `ResourceExhausted: consistent query buffer is full`
error seen when every UI refresh triggered a Query against a workflow that
was still draining a signal burst from load_starter.py.
"""

import asyncio
import logging
import sys
from contextlib import asynccontextmanager
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import AsyncIterator, Optional

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from temporalio.client import Client
from temporalio.envconfig import ClientConfig
from temporalio.exceptions import WorkflowAlreadyStartedError

# The FastAPI app is launched from the survey-poll directory
# (e.g. `uv run uvicorn ui.app:app`), so add the parent dir to sys.path
# to resolve `models` / `workflows` as flat modules.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from models import (  # noqa: E402
    AGGREGATOR_TASK_QUEUE,
    AGGREGATOR_WORKFLOW_ID,
    TallyResult,
)
from workflows import PollAggregatorWorkflow  # noqa: E402

logger = logging.getLogger(__name__)

POLL_INTERVAL_SECONDS = 0.5
QUERY_TIMEOUT = timedelta(seconds=30)

_client: Optional[Client] = None
_cache: Optional[TallyResult] = None
_last_poll_at: Optional[datetime] = None
_last_poll_error: Optional[str] = None


async def _poll_once() -> None:
    """Issue one Query against the aggregator and refresh the cache."""
    global _cache, _last_poll_at, _last_poll_error
    assert _client is not None
    try:
        handle = _client.get_workflow_handle(AGGREGATOR_WORKFLOW_ID)
        result: TallyResult = await handle.query(
            PollAggregatorWorkflow.tally, rpc_timeout=QUERY_TIMEOUT
        )
        _cache = result
        _last_poll_at = datetime.now(tz=timezone.utc)
        _last_poll_error = None
    except Exception as e:
        _last_poll_error = str(e)
        _last_poll_at = datetime.now(tz=timezone.utc)
        logger.warning("Tally poll failed: %s", e)


async def _poll_loop() -> None:
    """Background task: poll the aggregator forever at POLL_INTERVAL_SECONDS."""
    while True:
        await _poll_once()
        await asyncio.sleep(POLL_INTERVAL_SECONDS)


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    global _client
    config = ClientConfig.load_client_connect_config()
    _client = await Client.connect(**config)
    logger.info("Connected to Temporal Service")

    try:
        await _client.start_workflow(
            PollAggregatorWorkflow.run,
            None,
            id=AGGREGATOR_WORKFLOW_ID,
            task_queue=AGGREGATOR_TASK_QUEUE,
        )
        logger.info("Started aggregator workflow: id=%s", AGGREGATOR_WORKFLOW_ID)
    except WorkflowAlreadyStartedError:
        logger.info("Aggregator already running: id=%s", AGGREGATOR_WORKFLOW_ID)

    # Prime the cache before serving requests so the first /tally doesn't
    # return 503 while the background loop hasn't had a chance to run yet.
    await _poll_once()
    poller = asyncio.create_task(_poll_loop(), name="tally-poller")

    try:
        yield
    finally:
        poller.cancel()
        try:
            await poller
        except asyncio.CancelledError:
            pass


app = FastAPI(lifespan=_lifespan)


@app.get("/tally")
async def tally() -> dict:
    """Return the cached TallyResult plus freshness metadata.

    Does not issue a Temporal Query. The background poller refreshes the
    cache every POLL_INTERVAL_SECONDS.
    """
    payload: dict = {
        "counts": {},
        "total": 0,
        "last_updated": None,
        "cache_updated_at": _last_poll_at.isoformat() if _last_poll_at else None,
        "stale": _last_poll_error is not None,
        "error": _last_poll_error,
    }
    if _cache is not None:
        payload.update(asdict(_cache))
        # asdict overwrote cache_updated_at/stale/error with defaults; re-set.
        payload["cache_updated_at"] = (
            _last_poll_at.isoformat() if _last_poll_at else None
        )
        payload["stale"] = _last_poll_error is not None
        payload["error"] = _last_poll_error
    return payload


@app.post("/reset")
async def reset() -> dict:
    """Signal the aggregator to zero its live tally.

    S3 audit log is deliberately not touched. Existing response workflows
    are deliberately not terminated. See README for why.
    """
    if _client is None:
        raise HTTPException(status_code=503, detail="Temporal client not ready")
    try:
        handle = _client.get_workflow_handle(AGGREGATOR_WORKFLOW_ID)
        await handle.signal(PollAggregatorWorkflow.reset)
    except Exception as e:
        logger.warning("Reset signal failed: %s", e)
        raise HTTPException(status_code=502, detail=f"Reset signal failed: {e}")

    # Refresh the cache immediately so the dashboard reflects the reset on
    # the next poll instead of waiting up to POLL_INTERVAL_SECONDS.
    await _poll_once()
    return {"ok": True}


# Static files mounted last so /tally takes precedence.
_STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/", StaticFiles(directory=str(_STATIC_DIR), html=True), name="static")
