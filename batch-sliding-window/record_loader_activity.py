from dataclasses import dataclass
from typing import List

from temporalio import activity


@dataclass
class GetRecordsInput:
    """Input for the GetRecords activity."""
    page_size: int
    offset: int
    max_offset: int


@dataclass
class SingleRecord:
    """Represents a single record to be processed."""
    id: int


@dataclass
class GetRecordsOutput:
    """Output from the GetRecords activity."""
    records: List[SingleRecord]


class RecordLoader:
    """Activities for loading records from an external data source."""

    def __init__(self, record_count: int):
        self.record_count = record_count

    @activity.defn
    async def get_record_count(self) -> int:
        """Get the total record count.
        
        Used to partition processing across parallel sliding windows.
        The sample implementation just returns a fake value passed during worker initialization.
        """
        return self.record_count

    @activity.defn
    async def get_records(self, input: GetRecordsInput) -> GetRecordsOutput:
        """Get records loaded from an external data source.
        
        The sample returns fake records.
        """
        if input.max_offset > self.record_count:
            raise ValueError(f"max_offset({input.max_offset}) > record_count({self.record_count})")

        limit = min(input.offset + input.page_size, input.max_offset)
        records = [SingleRecord(id=i) for i in range(input.offset, limit)]
        
        return GetRecordsOutput(records=records) 