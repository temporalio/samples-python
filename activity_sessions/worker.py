import asyncio
import signal
from dataclasses import dataclass
from multiprocessing.queues import Queue
from multiprocessing.synchronize import Event

from temporalio.client import Client
from temporalio.envconfig import ClientConfig
from temporalio.worker import SingleSessionAdmission, Worker, WorkerSessionConfig

from activity_sessions import StepEvent
from activity_sessions.activities import ConversationActivities
from activity_sessions.workflows import ProcessConversation


@dataclass(frozen=True)
class WorkerSpec:
    identity: str
    # Dedicates the worker to one workflow for its lifetime, including across
    # restarts that reuse this identity.
    stable_identity: str | None = None


def worker_process(
    spec: WorkerSpec,
    task_queue: str,
    fetch_seconds: float,
    turn_seconds: float,
    events: "Queue[StepEvent]",
    ready: Event,
) -> None:
    async def run() -> None:
        config = ClientConfig.load_client_connect_config()
        config.setdefault("target_host", "localhost:7233")
        client = await Client.connect(**config, identity=spec.identity)
        activities = ConversationActivities(
            spec.identity, fetch_seconds, turn_seconds, events.put
        )
        admission = (
            SingleSessionAdmission(stable_identity=spec.stable_identity)
            if spec.stable_identity
            else None
        )
        async with Worker(
            client,
            task_queue=task_queue,
            workflows=[ProcessConversation],
            activities=[activities.conversation_step],
            session_config=WorkerSessionConfig(admission=admission),
            disable_eager_activity_execution=True,
        ):
            ready.set()
            # Run until the parent kills this process.
            await asyncio.Event().wait()

    # The parent handles Ctrl+C and stops every worker.
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    asyncio.run(run())
