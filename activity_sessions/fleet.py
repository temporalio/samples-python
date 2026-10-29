"""Worker processes, the turn events they send, and starting conversations."""

import argparse
import asyncio
import contextlib
import multiprocessing
import queue
from dataclasses import dataclass, field
from datetime import timedelta
from multiprocessing.process import BaseProcess
from multiprocessing.queues import Queue

from temporalio.client import Client, WorkflowHandle
from temporalio.envconfig import ClientConfig

from activity_sessions import StepEvent
from activity_sessions.worker import WorkerSpec, worker_process
from activity_sessions.workflows import ConversationInput, ProcessConversation

CONTEXT = multiprocessing.get_context("spawn")


@dataclass
class Turns:
    """Finished turns, built from the activities' events."""

    # Latest event per (workflow ID, step); a retried turn replaces its event.
    events: dict[tuple[str, int], StepEvent] = field(default_factory=dict)

    def drain(self, events: "Queue[StepEvent]") -> None:
        with contextlib.suppress(queue.Empty):
            while True:
                event = events.get_nowait()
                self.events[event.workflow_id, event.step] = event

    def of(self, workflow_id: str) -> list[StepEvent]:
        return [e for (w, _), e in sorted(self.events.items()) if w == workflow_id]

    def workflows_by_worker(self) -> dict[str, set[str]]:
        result: dict[str, set[str]] = {}
        for event in self.events.values():
            result.setdefault(event.worker, set()).add(event.workflow_id)
        return result


class Fleet:
    """Worker processes, each with a fresh interpreter, SDK runtime, and cache."""

    def __init__(
        self, task_queue: str, args: argparse.Namespace, events: "Queue[StepEvent]"
    ) -> None:
        self.worker_args = (task_queue, args.fetch_seconds, args.turn_seconds, events)
        self.processes: dict[str, BaseProcess] = {}

    async def start(self, *specs: WorkerSpec) -> None:
        """Start workers and return once every one of them is polling."""
        readies = []
        for spec in specs:
            ready = CONTEXT.Event()
            process = CONTEXT.Process(
                target=worker_process,
                args=(spec, *self.worker_args, ready),
                daemon=True,
            )
            process.start()
            self.processes[spec.identity] = process
            readies.append(ready)
        for ready in readies:
            await asyncio.to_thread(ready.wait)

    def kill(self, *identities: str) -> None:
        # SIGKILL: no graceful shutdown, like a crash.
        for identity in identities:
            process = self.processes.pop(identity)
            process.kill()
            process.join()

    def stop(self) -> None:
        self.kill(*self.processes)


async def connect() -> Client:
    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")
    return await Client.connect(**config)


async def start_conversations(
    client: Client, ids: list[str], task_queue: str, use_session: bool, steps: int
) -> list[WorkflowHandle]:
    return [
        await client.start_workflow(
            ProcessConversation.run,
            ConversationInput(use_session=use_session, steps=steps),
            id=workflow_id,
            task_queue=task_queue,
            execution_timeout=timedelta(minutes=5),
        )
        for workflow_id in ids
    ]


def new_event_queue() -> "Queue[StepEvent]":
    return CONTEXT.Queue()


def add_common_args(
    parser: argparse.ArgumentParser, fetch_seconds: float, turn_seconds: float
) -> None:
    parser.add_argument("--steps", type=int, default=6, help="Turns per workflow")
    parser.add_argument(
        "--fetch-seconds",
        type=float,
        default=fetch_seconds,
        help="Simulated latency of fetching one missing turn",
    )
    parser.add_argument(
        "--turn-seconds",
        type=float,
        default=turn_seconds,
        help="Simulated work per turn",
    )
