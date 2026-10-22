import asyncio
import os
import signal
from multiprocessing.synchronize import Event
from pathlib import Path

from temporalio.client import Client
from temporalio.envconfig import ClientConfig
from temporalio.worker import Worker, WorkerSessionOptions

from activity_sessions.activities import ConversationActivities
from activity_sessions.workflows import ProcessConversation


async def run_worker(
    identity: str,
    session_enabled: bool,
    task_queue: str,
    context_file: Path,
    stop: Event,
) -> None:
    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")
    client = await Client.connect(**config, identity=identity)
    activities = ConversationActivities(identity, session_enabled, context_file)
    worker = Worker(
        client,
        task_queue=task_queue,
        workflows=[ProcessConversation] if session_enabled else [],
        activities=[activities.conversation_step],
        session_worker_options=WorkerSessionOptions() if session_enabled else None,
        disable_eager_activity_execution=True,
        max_cached_workflows=100 if session_enabled else 0,
        max_concurrent_activities=2,
    )
    print(
        f"{identity} pid={os.getpid()} queue={task_queue} "
        f"session_support={'ON' if session_enabled else 'OFF'}",
        flush=True,
    )
    async with worker:
        await asyncio.to_thread(stop.wait)


def worker_process(
    identity: str,
    session_enabled: bool,
    task_queue: str,
    context_file: Path,
    stop: Event,
) -> None:
    # The parent handles Ctrl+C and releases all workers through the shared event.
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    asyncio.run(run_worker(identity, session_enabled, task_queue, context_file, stop))
