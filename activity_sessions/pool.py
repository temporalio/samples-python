import argparse
import asyncio
import signal
import sys
from contextlib import suppress
from pathlib import Path

from rich.console import Console

from activity_sessions import TASK_QUEUE, worker_configuration
from activity_sessions.display import print_worker_configuration


async def run_pool(
    workers: dict[str, bool], task_queue: str, context_file: Path
) -> None:
    console = Console()
    print_worker_configuration(workers, console)
    processes: dict[str, asyncio.subprocess.Process] = {}
    waiters: dict[asyncio.Task[int], str] = {}
    try:
        for identity, session_enabled in workers.items():
            args = [
                sys.executable,
                "-m",
                "activity_sessions.worker",
                "--identity",
                identity,
                "--task-queue",
                task_queue,
                "--context-file",
                str(context_file),
            ]
            if not session_enabled:
                args.append("--activity-only")
            processes[identity] = await asyncio.create_subprocess_exec(
                *args,
                # The pool forwards one interrupt, rather than children receiving Ctrl+C twice.
                start_new_session=sys.platform != "win32",
            )
        console.print(
            f"[cyan]Launched {len(processes)} independent worker processes on {task_queue}. "
            "Ctrl+C stops the whole pool.[/cyan]"
        )
        waiters = {
            asyncio.create_task(process.wait()): identity
            for identity, process in processes.items()
        }
        done, _ = await asyncio.wait(waiters, return_when=asyncio.FIRST_COMPLETED)
        exited = next(iter(done))
        raise RuntimeError(
            f"{waiters[exited]} exited unexpectedly with code {exited.result()}"
        )
    finally:
        for process in processes.values():
            if process.returncode is None:
                with suppress(ProcessLookupError):
                    if sys.platform == "win32":
                        process.terminate()
                    else:
                        process.send_signal(signal.SIGINT)
        try:
            await asyncio.wait_for(
                asyncio.gather(*(process.wait() for process in processes.values())), 15
            )
        except asyncio.TimeoutError:
            for process in processes.values():
                if process.returncode is None:
                    with suppress(ProcessLookupError):
                        process.kill()
            await asyncio.gather(*(process.wait() for process in processes.values()))
        await asyncio.gather(*waiters, return_exceptions=True)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Launch separate worker processes with private caches."
    )
    parser.add_argument("--session-workers", type=int, default=2)
    parser.add_argument("--activity-workers", type=int, default=0)
    parser.add_argument("--task-queue", default=TASK_QUEUE)
    parser.add_argument(
        "--context-file",
        type=Path,
        default=Path(__file__).with_name("conversation.txt"),
    )
    args = parser.parse_args()
    try:
        workers = worker_configuration(args.session_workers, args.activity_workers)
    except ValueError as error:
        parser.error(str(error))
    try:
        asyncio.run(run_pool(workers, args.task_queue, args.context_file))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
