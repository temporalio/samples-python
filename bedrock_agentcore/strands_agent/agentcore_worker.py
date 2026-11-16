"""Runs a Temporal Worker hosting a Strands agent inside an Amazon Bedrock
AgentCore Runtime.

The AgentCore SDK provides the HTTP contract: ``BedrockAgentCoreApp`` serves
/ping and /invocations, and reports "HealthyBusy" while an async task is
registered.

The Temporal Worker only starts *after* invocation, and it runs in the
background: /invocations registers an async task and acknowledges immediately
rather than holding the response open for the whole polling window. AgentCore
keeps the session alive for as long as /ping reports "HealthyBusy", which is
exactly what add_async_task/complete_async_task drive.

The Worker polls until it has been idle for AGENTCORE_DEBOUNCE_SECONDS. Because
the plugin runs the agent's model calls as Activities, and the code interpreter
tool is an Activity too, the interceptor below sees the agent's whole turn, so
the Worker is not torn down mid-thought.

Activity sessions (experimental): the plugin is built with
``session_options=ActivitySessionOptions(placement=UseWorkflowSession())``, so
every Activity the agent Workflow starts on this Task Queue -- the model calls
and ``execute_code`` -- runs on the *same* Worker, and therefore the same
AgentCore microVM, that holds the Workflow. The Worker is keyed to the
AgentCore session (``context.session_id``) with ``SingleSessionAdmission``, so
one runtime session serves exactly one Workflow for the Worker's lifetime. This
needs a Temporal Service with sticky activity execution enabled.
"""

import asyncio
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

from bedrock_agentcore.runtime import BedrockAgentCoreApp
from temporalio.client import Client
from temporalio.common import (
    ActivitySessionOptions,
    UseWorkflowSession,
    VersioningBehavior,
)
from temporalio.strands_agents import StrandsPlugin
from temporalio.worker import (
    ActivityInboundInterceptor,
    ExecuteActivityInput,
    Interceptor,
    SingleSessionAdmission,
    Worker,
    WorkerDeploymentConfig,
    WorkerDeploymentVersion,
    WorkerSessionConfig,
)

import workflows
from activities import execute_code

app = BedrockAgentCoreApp()
log = app.logger

# The background Worker, when one is running. Holds the strong reference that
# asyncio.create_task() does not keep, and doubles as the "already polling?" flag.
_worker: asyncio.Task[None] | None = None

DEPLOYMENT_NAME = os.environ.get("TEMPORAL_DEPLOYMENT_NAME", workflows.DEPLOYMENT_NAME)
BUILD_ID = os.environ.get("TEMPORAL_BUILD_ID", workflows.BUILD_ID)
TASK_QUEUE = os.environ.get("TEMPORAL_TASK_QUEUE", workflows.TASK_QUEUE)

# Activity slots and the sync-Activity thread pool are the same size. Session
# Workers require a fixed-size activity slot supplier, which is what
# max_concurrent_activities (without a tuner) gives.
ACTIVITY_SLOTS = 4

# @@@SNIPSTART python-agentcore-activity-tracker
# How long the Worker keeps polling after it goes idle.
DEBOUNCE = float(os.environ.get("AGENTCORE_DEBOUNCE_SECONDS", "60"))
# How long the drain waits for in-flight Activities (a model or tool call).
DRAIN = timedelta(seconds=120)


class ActivityTracker(Interceptor):
    """Tracks in-flight activities and blocks until AGENTCORE_DEBOUNCE_SECONDS elapses with no events."""

    def __init__(self) -> None:
        self.inflight = 0
        self.changed = asyncio.Event()

    def intercept_activity(
        self, next: ActivityInboundInterceptor
    ) -> ActivityInboundInterceptor:
        return _TrackedActivity(next, self)

    async def wait_until_idle(self, debounce: float) -> None:
        """Return once no Activity has run for ``debounce`` seconds."""
        while True:
            self.changed.clear()
            try:
                # Wake the moment an Activity starts or finishes; a timeout
                # instead means nothing has happened for the whole window.
                await asyncio.wait_for(self.changed.wait(), timeout=debounce)
            except asyncio.TimeoutError:
                if self.inflight == 0:
                    return


class _TrackedActivity(ActivityInboundInterceptor):
    def __init__(
        self, next: ActivityInboundInterceptor, tracker: ActivityTracker
    ) -> None:
        super().__init__(next)
        self._tracker = tracker

    async def execute_activity(self, input: ExecuteActivityInput):
        self._tracker.inflight += 1
        self._tracker.changed.set()
        log.info("activity in flight: %d", self._tracker.inflight)
        try:
            return await self.next.execute_activity(input)
        finally:
            self._tracker.inflight -= 1
            self._tracker.changed.set()


# @@@SNIPEND


# @@@SNIPSTART python-agentcore-activity-sessions
def session_config_for(session_id: str | None) -> WorkerSessionConfig:
    """Map the AgentCore runtime session to the Worker's session config.

    With a session id the Worker admits exactly one Workflow, bound under that
    id, so the AgentCore session and the Workflow session coincide. Without
    one (e.g. a local run) the Worker still serves Workflow sessions, just
    without single-session admission.
    """
    if session_id:
        return WorkerSessionConfig(
            admission=SingleSessionAdmission(stable_identity=session_id)
        )
    log.info("no AgentCore session id; worker sessions without admission")
    return WorkerSessionConfig()


def make_plugin() -> StrandsPlugin:
    """The Strands plugin, placing every same-queue Activity in the Workflow's session."""
    # Registered on the Client: Worker(...) merges its own kwargs, including
    # session_config, into the config *before* any plugin's configure_worker
    # runs, so the plugin's session_config check sees it.
    return StrandsPlugin(
        session_options=ActivitySessionOptions(placement=UseWorkflowSession())
    )


# @@@SNIPEND


# @@@SNIPSTART python-agentcore-runtime-handler
async def run_worker(session_id: str | None) -> None:
    """Poll until idle, then drain."""
    api_key = os.environ.get("TEMPORAL_API_KEY") or None
    client = await Client.connect(
        os.environ.get("TEMPORAL_ADDRESS", "localhost:7233"),
        namespace=os.environ.get("TEMPORAL_NAMESPACE", "default"),
        api_key=api_key,
        tls=bool(api_key),
        plugins=[make_plugin()],
    )

    tracker = ActivityTracker()
    log.info(
        "polling %s as %s/%s (session %s)",
        TASK_QUEUE,
        DEPLOYMENT_NAME,
        BUILD_ID,
        session_id,
    )
    # execute_code is a sync Activity, so it needs an executor to block on.
    with ThreadPoolExecutor(max_workers=ACTIVITY_SLOTS) as activity_executor:
        worker = Worker(
            client,
            task_queue=TASK_QUEUE,
            workflows=[workflows.StrandsAgentWorkflow],
            activities=[execute_code],
            activity_executor=activity_executor,
            max_concurrent_activities=ACTIVITY_SLOTS,
            session_config=session_config_for(session_id),
            interceptors=[tracker],
            deployment_config=WorkerDeploymentConfig(
                version=WorkerDeploymentVersion(
                    deployment_name=DEPLOYMENT_NAME, build_id=BUILD_ID
                ),
                use_worker_versioning=True,
                default_versioning_behavior=VersioningBehavior.PINNED,
            ),
            graceful_shutdown_timeout=DRAIN,
        )
        async with worker:
            await tracker.wait_until_idle(DEBOUNCE)
    log.info("worker idle for %ss; drained", DEBOUNCE)


async def _run_until_idle(task_id: int, session_id: str | None) -> None:
    """Own the Worker's whole life, and always release the async task."""
    try:
        await run_worker(session_id)
    except Exception:
        # Nothing awaits this task, so an error would otherwise be swallowed.
        log.exception("worker failed in async task")
    finally:
        # Without this the session stays HealthyBusy until MaxLifetime.
        app.complete_async_task(task_id)


@app.entrypoint
async def invoke(payload: dict, context) -> dict:
    """Start the Worker and acknowledge. The payload is unused."""
    session_id = context.session_id or None
    # Prevent duplicate workers since we exit early
    global _worker
    if _worker is not None and not _worker.done():
        log.info("worker already polling %s", TASK_QUEUE)
        return {"message": "worker already polling", "task_queue": TASK_QUEUE}

    task_id = app.add_async_task("temporal-worker")
    _worker = asyncio.create_task(_run_until_idle(task_id, session_id))

    return {"message": "worker starting", "task_queue": TASK_QUEUE}


# @@@SNIPEND

if __name__ == "__main__":
    app.run()
