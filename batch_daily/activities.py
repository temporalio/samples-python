import logging
from typing import List
from temporalio import activity

from dataclasses import dataclass

log = logging.getLogger(__name__)


@dataclass
class ListRecordActivityInput:
    record_filter: str
    day: str


@dataclass
class ProcessRecordActivityInput:
    uri: str


@activity.defn
def list_records(activity_input: ListRecordActivityInput) -> List[str]:
    log.info(
        f"filtering records on {activity_input.day} based on filter: {activity_input.record_filter}"
    )
    return [f"uri://record-id{idx}" for idx in range(10)]


@activity.defn
def process_record(activity_input: ProcessRecordActivityInput) -> str:
    log.info(f"this record is yummy: {activity_input.uri}")
    return activity_input.uri
