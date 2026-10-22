import argparse
import asyncio
import os
import signal
from contextlib import suppress
from pathlib import Path

from temporalio.client import Client
from temporalio.envconfig import ClientConfig
from temporalio.worker import Worker, WorkerSessionOptions

from activity_sessions import TASK_QUEUE
from activity_sessions.activities import ConversationActivities
from activity_sessions.workflows import ProcessConversation


async def run_worker(
    identity: str, activity_only: bool, task_queue: str, context_file: Path
) -> None:
    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")
    client = await Client.connect(**config, identity=identity)
    session_enabled = not activity_only
    activities = ConversationActivities(identity, session_enabled, context_file)
    stop = asyncio.Event()
    for signum in (signal.SIGINT, signal.SIGTERM):
        with suppress(NotImplementedError):
            asyncio.get_running_loop().add_signal_handler(signum, stop.set)
    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[ProcessConversation] if session_enabled else [],
        activities=[activities.conversation_step],
        session_worker_options=WorkerSessionOptions() if session_enabled else None,
        disable_eager_activity_execution=True,
        max_cached_workflows=100 if session_enabled else 0,
        max_concurrent_activities=2,
    ):
        print(
            f"{identity} pid={os.getpid()} queue={task_queue} "
            f"session_support={'ON' if session_enabled else 'OFF'}",
            flush=True,
        )
        await stop.wait()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--identity", required=True)
    parser.add_argument("--activity-only", action="store_true")
    parser.add_argument("--task-queue", default=TASK_QUEUE)
    parser.add_argument(
        "--context-file",
        type=Path,
        default=Path(__file__).with_name("conversation.txt"),
    )
    args = parser.parse_args()
    try:
        asyncio.run(
            run_worker(
                args.identity, args.activity_only, args.task_queue, args.context_file
            )
        )
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
