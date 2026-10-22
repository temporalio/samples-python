import argparse
import asyncio
import os
import signal
from contextlib import suppress
from datetime import timedelta
from pathlib import Path

from temporalio.client import Client
from temporalio.envconfig import ClientConfig
from temporalio.worker import PollerBehaviorSimpleMaximum, Worker, WorkerSessionOptions

from activity_sessions import TASK_QUEUE
from activity_sessions.activities import ConversationActivities
from activity_sessions.models import WorkerRegistration
from activity_sessions.storage import FileArtifactStore
from activity_sessions.workflows import ProcessConversation


async def run_worker(
    identity: str, activity_only: bool, task_queue: str, store_directory: Path
) -> None:
    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")
    client = await Client.connect(**config, identity=identity)
    session_enabled = not activity_only
    store = FileArtifactStore(store_directory)
    activities = ConversationActivities(store, identity, session_enabled)
    registration = WorkerRegistration(
        identity, session_enabled, os.getpid(), task_queue
    )
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for signum in (signal.SIGINT, signal.SIGTERM):
        with suppress(NotImplementedError):
            loop.add_signal_handler(signum, stop.set)

    store.register_worker(registration)
    try:
        async with Worker(
            client,
            task_queue=task_queue,
            workflows=[ProcessConversation] if session_enabled else [],
            activities=[activities.process_conversation_step],
            session_worker_options=WorkerSessionOptions() if session_enabled else None,
            disable_eager_activity_execution=True,
            max_cached_workflows=100 if session_enabled else 0,
            max_concurrent_activities=2,
            workflow_task_poller_behavior=PollerBehaviorSimpleMaximum(2),
            activity_task_poller_behavior=PollerBehaviorSimpleMaximum(2),
            sticky_queue_schedule_to_start_timeout=timedelta(minutes=1),
        ):
            print(
                f"Worker {identity} pid={os.getpid()} queue={task_queue} "
                f"session_polling={'ON' if session_enabled else 'OFF'} "
                f"role={'workflow+activity' if session_enabled else 'activity-only'} "
                f"store={store_directory.resolve()}",
                flush=True,
            )
            await stop.wait()
    finally:
        store.unregister_worker(registration)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run one process with its own activity cache."
    )
    parser.add_argument("--identity", required=True)
    parser.add_argument("--activity-only", action="store_true")
    parser.add_argument("--task-queue", default=TASK_QUEUE)
    parser.add_argument(
        "--store-dir", type=Path, default=Path("activity_sessions/.data")
    )
    args = parser.parse_args()
    try:
        asyncio.run(
            run_worker(
                args.identity, args.activity_only, args.task_queue, args.store_dir
            )
        )
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
