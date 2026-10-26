import asyncio
import time
import random
from typing import Any, Dict, List
from temporalio import activity

from dataclasses import dataclass


@dataclass
class ListRecordActivityInput:
    record_filter: str
    day: str


@dataclass
class ProcessRecordActivityInput:
    uri: str


async def random_sleep():
    """
    simulate a long running operation with a random sleep.
    """
    sleep_s = 1 / random.randint(1, 100)
    await asyncio.sleep(sleep_s)


@activity.defn
async def list_records(activity_input: ListRecordActivityInput) -> List[str]:
    print(
        f"filtering records on {activity_input.day} based on filter: {activity_input.record_filter}"
    )
    await random_sleep()
    return [f"uri://record-id{idx}" for idx in range(10)]


@activity.defn
async def process_record(activity_input: ProcessRecordActivityInput) -> Dict[str, Any]:
    t0 = time.monotonic()
    print(f"this record is yummy: {activity_input.uri}")
    await random_sleep()
    return {"runtime": time.monotonic() - t0}
