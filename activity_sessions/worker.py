import asyncio
import signal
from multiprocessing.queues import Queue
from multiprocessing.synchronize import Barrier

from temporalio.client import Client
from temporalio.envconfig import ClientConfig
from temporalio.worker import Worker, WorkerSessionOptions

from activity_sessions import StepEvent
from activity_sessions.activities import ConversationActivities
from activity_sessions.workflows import ProcessConversation


async def run_worker(
    identity: str,
    session_enabled: bool,
    task_queue: str,
    fetch_seconds: float,
    events: "Queue[StepEvent]",
    ready: Barrier,
) -> None:
    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")
    client = await Client.connect(**config, identity=identity)
    activities = ConversationActivities(identity, fetch_seconds, events.put)
    worker = Worker(
        client,
        task_queue=task_queue,
        workflows=[ProcessConversation] if session_enabled else [],
        activities=[activities.conversation_step],
        session_worker_options=WorkerSessionOptions() if session_enabled else None,
        disable_eager_activity_execution=True,
        max_concurrent_activities=100,
    )
    async with worker:
        await asyncio.to_thread(ready.wait)
        # Run until the parent terminates this process.
        await asyncio.Event().wait()


def worker_process(
    identity: str,
    session_enabled: bool,
    task_queue: str,
    fetch_seconds: float,
    events: "Queue[StepEvent]",
    ready: Barrier,
) -> None:
    # The parent handles Ctrl+C and terminates every worker.
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    asyncio.run(
        run_worker(identity, session_enabled, task_queue, fetch_seconds, events, ready)
    )
