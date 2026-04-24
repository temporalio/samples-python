"""Load generator for the survey-poll sample.

Drives a configurable rate of SurveyResponseWorkflow starts against the shared
task queue `tq-survey-replay2026`. Both the local survey-poll worker and the
serverless Lambda variant poll this queue under the same Worker Deployment
version (`survey-replay2026/v1`). With the local worker's
`max_concurrent_activities=1`, any parallel load immediately backs up the
activity task queue and provokes Lambda scale-ups.

Each respondent becomes one workflow; answers are sampled from a configurable
Yes/No/Maybe distribution. Workflow IDs embed a per-run prefix so re-runs never
collide. Fire-and-forget `start_workflow` is bounded by a semaphore for
backpressure.

See pi-worker/load_starter.py for the original implementation this is ported
from — the burst/ramp shape and safety rails are identical.
"""

import argparse
import asyncio
import logging
import random
import signal
import time
import uuid
from collections import Counter
from dataclasses import dataclass
from typing import List

from temporalio.client import Client, WorkflowHandle
from temporalio.envconfig import ClientConfig

from models import TASK_QUEUE, SurveyResponse, SurveyResponseInput
from workflows import SurveyResponseWorkflow

RESPONSES = [SurveyResponse.YES, SurveyResponse.MAYBE, SurveyResponse.NO]


@dataclass
class LoadStats:
    started: int = 0
    failed_to_start: int = 0
    completed: int = 0
    failed: int = 0


async def _start_one(
    client: Client,
    *,
    run_id: str,
    index: int,
    weights: List[float],
    stats: LoadStats,
    tally: Counter,
    handles: List[WorkflowHandle],
) -> None:
    user_id = f"user-{run_id}-{index:06d}"
    workflow_id = f"survey-replay2026-{user_id}"
    answer = random.choices(RESPONSES, weights=weights, k=1)[0]
    input = SurveyResponseInput(user_id=user_id, response=answer)
    try:
        handle = await client.start_workflow(
            SurveyResponseWorkflow.run,
            input,
            id=workflow_id,
            task_queue=TASK_QUEUE,
        )
        stats.started += 1
        tally[answer.value] += 1
        handles.append(handle)
    except Exception as e:
        stats.failed_to_start += 1
        logging.warning("start_workflow failed for %s: %s", workflow_id, e)


def _ramp_rate(elapsed: float, ramp_seconds: float, peak_rate: float) -> float:
    if ramp_seconds <= 0 or elapsed >= ramp_seconds:
        return peak_rate
    fraction = max(elapsed / ramp_seconds, 0.01)
    return peak_rate * fraction


async def _drive_ramp(
    client: Client,
    *,
    run_id: str,
    weights: List[float],
    stats: LoadStats,
    tally: Counter,
    handles: List[WorkflowHandle],
    ramp_seconds: float,
    peak_rate: float,
    sustain_seconds: float,
    max_inflight: int,
    stop_event: asyncio.Event,
) -> None:
    sem = asyncio.Semaphore(max_inflight)
    launches: List[asyncio.Task] = []
    index = 0
    total_seconds = ramp_seconds + sustain_seconds
    start = time.monotonic()
    last_report = start

    async def bounded(i: int) -> None:
        async with sem:
            await _start_one(
                client,
                run_id=run_id,
                index=i,
                weights=weights,
                stats=stats,
                tally=tally,
                handles=handles,
            )

    while not stop_event.is_set():
        now = time.monotonic()
        elapsed = now - start
        if elapsed >= total_seconds:
            break
        rate = _ramp_rate(elapsed, ramp_seconds, peak_rate)
        interval = 1.0 / rate if rate > 0 else 1.0

        launches.append(asyncio.create_task(bounded(index)))
        index += 1

        if now - last_report >= 5.0:
            logging.info(
                "t=%5.1fs rate=%5.2f/s started=%d failed_to_start=%d inflight=%d",
                elapsed,
                rate,
                stats.started,
                stats.failed_to_start,
                max_inflight - sem._value,  # type: ignore[attr-defined]
            )
            last_report = now

        try:
            await asyncio.wait_for(stop_event.wait(), timeout=interval)
            break
        except asyncio.TimeoutError:
            pass

    if launches:
        logging.info("Draining %d pending start calls...", len(launches))
        await asyncio.gather(*launches, return_exceptions=True)


async def _drive_burst(
    client: Client,
    *,
    run_id: str,
    weights: List[float],
    stats: LoadStats,
    tally: Counter,
    handles: List[WorkflowHandle],
    burst_size: int,
    max_inflight: int,
    stop_event: asyncio.Event,
) -> None:
    sem = asyncio.Semaphore(max_inflight)

    async def bounded(i: int) -> None:
        async with sem:
            await _start_one(
                client,
                run_id=run_id,
                index=i,
                weights=weights,
                stats=stats,
                tally=tally,
                handles=handles,
            )

    logging.info(
        "Firing burst of %d workflows (max_inflight=%d)", burst_size, max_inflight
    )
    tasks = [asyncio.create_task(bounded(i)) for i in range(burst_size)]

    async def wait_all() -> None:
        await asyncio.gather(*tasks, return_exceptions=True)

    done_task = asyncio.create_task(wait_all())
    stop_task = asyncio.create_task(stop_event.wait())
    try:
        await asyncio.wait({done_task, stop_task}, return_when=asyncio.FIRST_COMPLETED)
        if not done_task.done():
            logging.info("Stop requested; cancelling remaining burst starts")
            for t in tasks:
                t.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
    finally:
        stop_task.cancel()


async def _await_results(
    handles: List[WorkflowHandle],
    stats: LoadStats,
    timeout: float,
) -> None:
    async def wait_one(h: WorkflowHandle) -> None:
        try:
            await h.result()
            stats.completed += 1
        except Exception:
            stats.failed += 1

    tasks = [asyncio.create_task(wait_one(h)) for h in handles]
    try:
        await asyncio.wait_for(
            asyncio.gather(*tasks, return_exceptions=True), timeout=timeout
        )
    except asyncio.TimeoutError:
        logging.warning(
            "Timed out after %.0fs awaiting results; %d still pending",
            timeout,
            len(tasks) - stats.completed - stats.failed,
        )
        for t in tasks:
            t.cancel()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Load generator that drives SurveyResponseWorkflow starts to "
            "provoke serverless scale-ups alongside the local survey-poll worker."
        )
    )
    parser.add_argument(
        "--mode",
        choices=("ramp", "burst"),
        default="ramp",
        help=(
            "ramp: linearly ramp up then sustain. "
            "burst: fire N workflows as fast as --max-inflight allows."
        ),
    )
    parser.add_argument(
        "--ramp-seconds",
        type=float,
        default=60.0,
        help="[ramp] Ramp-up duration (default: 60).",
    )
    parser.add_argument(
        "--peak-rate",
        type=float,
        default=1.0,
        help="[ramp] Peak workflow starts per second (default: 1.0).",
    )
    parser.add_argument(
        "--sustain-seconds",
        type=float,
        default=180.0,
        help="[ramp] Time to hold at peak (default: 180).",
    )
    parser.add_argument(
        "--burst-size",
        type=int,
        default=50,
        help="[burst] Number of workflows to fire (default: 50).",
    )
    parser.add_argument(
        "--max-inflight",
        type=int,
        default=20,
        help="Max concurrent start_workflow RPCs (default: 20).",
    )

    parser.add_argument(
        "--yes-pct",
        type=float,
        default=60.0,
        help="Percent of respondents voting Yes (default: 60).",
    )
    parser.add_argument(
        "--maybe-pct",
        type=float,
        default=30.0,
        help="Percent of respondents voting Maybe (default: 30).",
    )
    parser.add_argument(
        "--no-pct",
        type=float,
        default=10.0,
        help="Percent of respondents voting No (default: 10).",
    )

    parser.add_argument(
        "--wait-for-results",
        action="store_true",
        help="Await every started workflow after the load phase.",
    )
    parser.add_argument(
        "--result-timeout",
        type=float,
        default=900.0,
        help="Timeout (seconds) for --wait-for-results (default: 900).",
    )
    parser.add_argument(
        "--run-id",
        default=None,
        help="Prefix for user IDs. Defaults to a random 8-char hex.",
    )
    args = parser.parse_args()

    total = args.yes_pct + args.maybe_pct + args.no_pct
    if abs(total - 100.0) > 0.01:
        parser.error(
            f"--yes-pct + --maybe-pct + --no-pct must sum to 100 (got {total})"
        )
    if min(args.yes_pct, args.maybe_pct, args.no_pct) < 0:
        parser.error("vote percentages must be non-negative")
    return args


async def main() -> None:
    args = _parse_args()
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
    )

    config = ClientConfig.load_client_connect_config()
    client = await Client.connect(**config)
    logging.info("Connected to Temporal Service")

    run_id = args.run_id or uuid.uuid4().hex[:8]
    # Order matches RESPONSES: [YES, MAYBE, NO].
    weights = [args.yes_pct, args.maybe_pct, args.no_pct]
    stats = LoadStats()
    tally: Counter = Counter()
    handles: List[WorkflowHandle] = []
    stop_event = asyncio.Event()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop_event.set)
        except NotImplementedError:
            pass  # Windows fallback

    logging.info(
        "Mode=%s run_id=%s task_queue=%s distribution=yes:%.0f%% maybe:%.0f%% no:%.0f%%",
        args.mode,
        run_id,
        TASK_QUEUE,
        args.yes_pct,
        args.maybe_pct,
        args.no_pct,
    )

    t0 = time.monotonic()
    if args.mode == "ramp":
        approx_total = int(
            args.peak_rate * args.sustain_seconds
            + args.peak_rate * args.ramp_seconds / 2
        )
        logging.info(
            "ramp: ramp=%ss peak=%s/s sustain=%ss max_inflight=%d (~%d projected)",
            args.ramp_seconds,
            args.peak_rate,
            args.sustain_seconds,
            args.max_inflight,
            approx_total,
        )
        await _drive_ramp(
            client,
            run_id=run_id,
            weights=weights,
            stats=stats,
            tally=tally,
            handles=handles,
            ramp_seconds=args.ramp_seconds,
            peak_rate=args.peak_rate,
            sustain_seconds=args.sustain_seconds,
            max_inflight=args.max_inflight,
            stop_event=stop_event,
        )
    else:
        await _drive_burst(
            client,
            run_id=run_id,
            weights=weights,
            stats=stats,
            tally=tally,
            handles=handles,
            burst_size=args.burst_size,
            max_inflight=args.max_inflight,
            stop_event=stop_event,
        )

    elapsed = time.monotonic() - t0
    logging.info(
        "Load phase done in %.1fs: started=%d failed_to_start=%d tally yes=%d maybe=%d no=%d",
        elapsed,
        stats.started,
        stats.failed_to_start,
        tally[SurveyResponse.YES.value],
        tally[SurveyResponse.MAYBE.value],
        tally[SurveyResponse.NO.value],
    )

    if args.wait_for_results and handles:
        logging.info(
            "Awaiting %d workflow results (timeout=%.0fs)...",
            len(handles),
            args.result_timeout,
        )
        await _await_results(handles, stats, args.result_timeout)
        logging.info(
            "Final: started=%d completed=%d failed=%d pending=%d",
            stats.started,
            stats.completed,
            stats.failed,
            stats.started - stats.completed - stats.failed,
        )


if __name__ == "__main__":
    asyncio.run(main())
