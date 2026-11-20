"""Runs a Temporal Worker hosting an OpenAI Agents SDK agent inside an Amazon Bedrock
AgentCore Runtime.

The AgentCore SDK provides the HTTP contract: ``BedrockAgentCoreApp`` serves
/ping and /invocations, and reports "HealthyBusy" while an async task is
registered.

The Temporal Worker only starts *after* invocation, and it runs in the
background: /invocations registers an async task and acknowledges immediately
rather than holding the response open for the whole polling window. AgentCore
keeps the session alive for as long as /ping reports "HealthyBusy", which is
exactly what add_async_task/complete_async_task drive.

The Worker polls until it has been idle for AGENTCORE_DEBOUNCE_SECONDS. The
WorkTracker below counts in-flight Workflow and Nexus tasks (through the slot
supplier) as well as Activities (through an interceptor). Because the plugin
runs the agent's model calls as Activities, and the code interpreter tool is an
Activity too, it sees the agent's whole turn, so the Worker is not torn down
mid-thought.

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
from temporalio.openai_agents import ModelActivityParameters, OpenAIAgentsPlugin
from temporalio.worker import (
    ActivityInboundInterceptor,
    CustomSlotSupplier,
    ExecuteActivityInput,
    FixedSizeSlotSupplier,
    Interceptor,
    SingleSessionAdmission,
    SlotMarkUsedContext,
    SlotPermit,
    SlotReleaseContext,
    SlotReserveContext,
    Worker,
    WorkerDeploymentConfig,
    WorkerDeploymentVersion,
    WorkerSessionConfig,
    WorkerTuner,
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
# Workers require a fixed-size activity slot supplier, so the tuner below uses
# FixedSizeSlotSupplier for activities.
ACTIVITY_SLOTS = 4
# Per-type limit for the other task types, matching the SDK's max_concurrent_*
# defaults (a custom tuner replaces those arguments, so it is enforced here).
SLOTS_PER_TYPE = 100

# @@@SNIPSTART python-agentcore-openai-activity-tracker
# How long the Worker keeps polling after it goes idle.
DEBOUNCE = float(os.environ.get("AGENTCORE_DEBOUNCE_SECONDS", "60"))
# How long the drain waits for in-flight Activities (a model or tool call).
DRAIN = timedelta(seconds=120)


class WorkTracker(Interceptor):
    """Counts in-flight work and blocks until AGENTCORE_DEBOUNCE_SECONDS elapses with no events.

    Two sources feed the count:
    - Workflow and Nexus tasks, through _TrackingSlotSupplier: a slot is in use
      from when Core hands the Worker a polled task until it completes, so this
      covers starts, signals, updates, queries, timer fires and activity results.
    - Activities and local activities, through the activity interceptor below.
      Session Workers require a fixed-size activity slot supplier (the SDK
      rejects a custom one), so activities cannot be tracked by slot.

    A Workflow merely waiting (e.g. for the next prompt) holds no slot, so the
    Worker can still go idle and let AgentCore reap the session.

    Only touched from the event loop thread; see _TrackingSlotSupplier.
    """

    def __init__(self) -> None:
        self.inflight = 0
        self.changed = asyncio.Event()

    def begin(self) -> None:
        self.inflight += 1
        self.changed.set()

    def end(self) -> None:
        self.inflight -= 1
        self.changed.set()

    def intercept_activity(
        self, next: ActivityInboundInterceptor
    ) -> ActivityInboundInterceptor:
        return _TrackedActivity(next, self)

    def tuner(self, loop: asyncio.AbstractEventLoop) -> WorkerTuner:
        """A tuner whose Workflow and Nexus slots report their use to this tracker."""

        def tracked(kind: str) -> "_TrackingSlotSupplier":
            return _TrackingSlotSupplier(self, loop, kind, SLOTS_PER_TYPE)

        return WorkerTuner.create_composite(
            workflow_supplier=tracked("workflow"),
            activity_supplier=FixedSizeSlotSupplier(ACTIVITY_SLOTS),
            local_activity_supplier=FixedSizeSlotSupplier(SLOTS_PER_TYPE),
            nexus_supplier=tracked("nexus"),
        )

    async def wait_until_idle(self, debounce: float) -> None:
        """Return once no work has started or finished for ``debounce`` seconds."""
        while True:
            self.changed.clear()
            try:
                # Wake the moment a task starts or finishes; a timeout instead
                # means nothing has happened for the whole window.
                await asyncio.wait_for(self.changed.wait(), timeout=debounce)
            except asyncio.TimeoutError:
                if self.inflight == 0:
                    return


class _TrackedActivity(ActivityInboundInterceptor):
    def __init__(self, next: ActivityInboundInterceptor, tracker: WorkTracker) -> None:
        super().__init__(next)
        self._tracker = tracker

    async def execute_activity(self, input: ExecuteActivityInput):
        # The interceptor runs on the event loop (even for sync Activities), so
        # the tracker can be touched directly.
        self._tracker.begin()
        log.info("activity in flight (in flight: %d)", self._tracker.inflight)
        try:
            return await self.next.execute_activity(input)
        finally:
            self._tracker.end()


class _TrackingSlotSupplier(CustomSlotSupplier):
    """Fixed-size slot supplier that reports slot use to a WorkTracker.

    Core reserves slots ahead of time (one per waiting poller), so reservation
    is not work: a slot counts as busy only between mark_slot_used and
    release_slot. Those two are called from Core threads (sometimes while
    Core holds internal locks), so they only hop onto the event loop with
    call_soon_threadsafe and never block.
    """

    def __init__(
        self,
        tracker: WorkTracker,
        loop: asyncio.AbstractEventLoop,
        kind: str,
        limit: int,
    ) -> None:
        self._tracker = tracker
        self._loop = loop
        self._kind = kind
        self._sem = asyncio.Semaphore(limit)

    async def reserve_slot(self, ctx: SlotReserveContext) -> SlotPermit:
        # Runs on the event loop, before each poll.
        await self._sem.acquire()
        return SlotPermit()

    def try_reserve_slot(self, ctx: SlotReserveContext) -> SlotPermit | None:
        # Eager tasks: decline, and they are delivered through normal polling.
        return None

    def mark_slot_used(self, ctx: SlotMarkUsedContext) -> None:
        self._loop.call_soon_threadsafe(self._used)

    def release_slot(self, ctx: SlotReleaseContext) -> None:
        self._loop.call_soon_threadsafe(self._released, ctx.slot_info is not None)

    def _used(self) -> None:
        self._tracker.begin()
        log.info("%s slot in use (in flight: %d)", self._kind, self._tracker.inflight)

    def _released(self, was_used: bool) -> None:
        self._sem.release()
        if was_used:
            self._tracker.end()


# @@@SNIPEND


# @@@SNIPSTART python-agentcore-openai-activity-sessions
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


def make_plugin() -> OpenAIAgentsPlugin:
    """The OpenAI Agents plugin, placing every same-queue Activity in the Workflow's session."""
    # Registered on the Client: Worker(...) merges its own kwargs, including
    # session_config, into the config *before* any plugin's configure_worker
    # runs, so the plugin's session_config check sees it.
    return OpenAIAgentsPlugin(
        model_params=ModelActivityParameters(
            start_to_close_timeout=timedelta(seconds=60)
        ),
        session_options=ActivitySessionOptions(placement=UseWorkflowSession()),
    )


# @@@SNIPEND


# @@@SNIPSTART python-agentcore-openai-runtime-handler
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

    tracker = WorkTracker()
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
            workflows=[workflows.OpenAIAgentWorkflow],
            activities=[execute_code],
            activity_executor=activity_executor,
            session_config=session_config_for(session_id),
            interceptors=[tracker],
            tuner=tracker.tuner(asyncio.get_running_loop()),
            deployment_config=WorkerDeploymentConfig(
                version=WorkerDeploymentVersion(
                    deployment_name=DEPLOYMENT_NAME, build_id=BUILD_ID
                ),
                use_worker_versioning=True,
                default_versioning_behavior=VersioningBehavior.PINNED,
            ),
            identity=f"SessionWorker={session_id}",
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
