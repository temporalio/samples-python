"""Break-glass: fire N async Lambda invocations against the survey-poll worker.

Bypasses Temporal entirely. Mirrors the controller's invocation shape
(`InvocationType=Event`, no payload, no qualifier) so each invocation behaves
identically to a controller-triggered scale-up. Use when the local worker is
down or the auto-scaling controller is paused, and the activity backlog needs
manual relief.
"""

import argparse
import asyncio
import logging
import time

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError


async def _invoke_one(
    client,
    *,
    function_arn: str,
    counters: dict,
) -> None:
    try:
        await asyncio.to_thread(
            client.invoke,
            FunctionName=function_arn,
            InvocationType="Event",
        )
        counters["invoked"] += 1
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        if code == "TooManyRequestsException":
            counters["throttled"] += 1
            logging.warning("Throttled by Lambda: %s", e)
        else:
            counters["failed"] += 1
            logging.warning("Invoke failed: %s", e)
    except Exception as e:
        counters["failed"] += 1
        logging.warning("Invoke failed: %s", e)


async def _drive(
    client,
    *,
    function_arn: str,
    count: int,
    max_inflight: int,
) -> dict:
    sem = asyncio.Semaphore(max_inflight)
    counters = {"invoked": 0, "failed": 0, "throttled": 0}

    async def bounded() -> None:
        async with sem:
            await _invoke_one(client, function_arn=function_arn, counters=counters)

    await asyncio.gather(*(bounded() for _ in range(count)))
    return counters


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Manually fire N async Lambda invocations against the survey-poll "
            "worker. Bypasses Temporal's auto-scaling controller."
        )
    )
    parser.add_argument(
        "--function-arn",
        required=True,
        help="Lambda ARN, partial ARN, or function name.",
    )
    parser.add_argument("--region", required=True, help="AWS region.")
    parser.add_argument(
        "--count", type=int, required=True, help="Number of Invoke calls."
    )
    parser.add_argument(
        "--max-inflight",
        type=int,
        default=10,
        help="Max concurrent Invoke RPCs (default: 10).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print plan and exit without calling AWS.",
    )
    args = parser.parse_args()
    if args.count < 1:
        parser.error("--count must be >= 1")
    if args.max_inflight < 1:
        parser.error("--max-inflight must be >= 1")
    return args


async def main() -> None:
    args = _parse_args()
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
    )

    logging.info(
        "Plan: invoke function=%s region=%s count=%d max_inflight=%d",
        args.function_arn,
        args.region,
        args.count,
        args.max_inflight,
    )
    if args.dry_run:
        logging.info("Dry run — no AWS calls made.")
        return

    config = Config(
        read_timeout=10,
        connect_timeout=5,
        retries={"max_attempts": 0},
    )
    client = boto3.client("lambda", region_name=args.region, config=config)

    t0 = time.monotonic()
    counters = await _drive(
        client,
        function_arn=args.function_arn,
        count=args.count,
        max_inflight=args.max_inflight,
    )
    elapsed = time.monotonic() - t0

    logging.info(
        "Lambda invoke phase done in %.1fs: invoked=%d failed=%d throttled=%d",
        elapsed,
        counters["invoked"],
        counters["failed"],
        counters["throttled"],
    )


if __name__ == "__main__":
    asyncio.run(main())
